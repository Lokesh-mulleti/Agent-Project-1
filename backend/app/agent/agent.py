"""
Agent execution engine and tool orchestration framework.
Supports Google Gemini, OpenAI, and a built-in heuristic Mock engine.
"""

import json
import logging
import inspect
import re
from typing import Callable, Dict, Any, List, Optional, Tuple

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.calculator import calculate
from app.tools.currency import convert_currency
from app.tools.doc_reader import read_document
from app.tools.weather import get_weather
from app.tools.search import search_web

logger = logging.getLogger("ai_agent")


class ToolRegistry:
    """
    Registry for functions that can be dynamically called by LLMs.
    Automatically generates JSON schemas for tool-use configurations.
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}

    def register(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """Registers a callable function and generates its schema."""
        tool_name = name or func.__name__
        self._tools[tool_name] = func
        self._schemas[tool_name] = self._generate_schema(func, tool_name, description)
        logger.debug(f"Registered tool '{tool_name}'")

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """Returns tool definitions formatted for OpenAI Function Calling."""
        return [
            {"type": "function", "function": schema}
            for schema in self._schemas.values()
        ]

    def get_gemini_tools(self, types_module) -> List[Any]:
        """Returns tools formatted as Gemini FunctionDeclarations."""
        declarations = []
        for schema in self._schemas.values():
            props = {}
            for p_name, p_info in schema["parameters"]["properties"].items():
                p_type = p_info["type"].upper()
                type_enum = getattr(types_module.Type, p_type, types_module.Type.STRING)
                props[p_name] = types_module.Schema(
                    type=type_enum,
                    description=p_info.get("description", ""),
                )

            declaration = types_module.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parameters=types_module.Schema(
                    type=types_module.Type.OBJECT,
                    properties=props,
                    required=schema["parameters"].get("required", []),
                ),
            )
            declarations.append(declaration)

        return [types_module.Tool(function_declarations=declarations)] if declarations else []

    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """Invokes a registered tool by name with arguments and handles exceptions."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' is not registered."

        try:
            sig = inspect.signature(tool)
            bound_args = sig.bind_partial(**arguments)
            bound_args.apply_defaults()
            result = tool(*bound_args.args, **bound_args.kwargs)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            return f"Tool Execution Error ({name}): {str(e)}"

    def _generate_schema(self, func: Callable, name: str, custom_desc: Optional[str] = None) -> Dict[str, Any]:
        """Generates JSON schema from function signature and docstrings."""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or custom_desc or f"Tool for {name}"

        properties: Dict[str, Any] = {}
        required: List[str] = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")

            param_info: Dict[str, Any] = {
                "type": param_type,
                "description": f"Parameter: {param_name}",
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = param_info

        return {
            "name": name,
            "description": doc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


class BaseAgentBackend:
    """Base class for agent provider execution backends."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def run(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        raise NotImplementedError


class GeminiAgentBackend(BaseAgentBackend):
    """Execution backend using official Google GenAI SDK (`google-genai`)."""

    def __init__(self, registry: ToolRegistry):
        super().__init__(registry)
        from google import genai
        from google.genai import types

        api_key = settings.get_gemini_key()
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model = settings.gemini_model
        self.types = types
        self.chat_session = None

    def run(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        tools = self.registry.get_gemini_tools(self.types)
        config = self.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=settings.temperature,
            tools=tools,
        )

        gemini_contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_contents.append(
                self.types.Content(
                    role=role,
                    parts=[self.types.Part.from_text(text=msg["content"])],
                )
            )

        gemini_contents.append(
            self.types.Content(
                role="user",
                parts=[self.types.Part.from_text(text=user_message)],
            )
        )

        iteration = 0
        final_text = ""

        while iteration < settings.max_iterations:
            iteration += 1
            response = self.client.models.generate_content(
                model=self.model,
                contents=gemini_contents,
                config=config,
            )

            function_calls = []
            candidate = response.candidates[0] if response.candidates else None
            if candidate and candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)

            if not function_calls:
                final_text = response.text or "Completed without additional output."
                break

            gemini_contents.append(candidate.content)

            function_response_parts = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}

                if callbacks and "on_tool_call" in callbacks:
                    callbacks["on_tool_call"](tool_name, tool_args)

                tool_result_str = self.registry.execute(tool_name, tool_args)

                if callbacks and "on_tool_result" in callbacks:
                    callbacks["on_tool_result"](tool_name, tool_result_str)

                function_response_parts.append(
                    self.types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_result_str},
                    )
                )

            gemini_contents.append(
                self.types.Content(role="user", parts=function_response_parts)
            )

        updated_history = list(history)
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": final_text})
        return final_text, updated_history


class OpenAIAgentBackend(BaseAgentBackend):
    """Execution backend using OpenAI Python SDK."""

    def __init__(self, registry: ToolRegistry):
        super().__init__(registry)
        from openai import OpenAI

        api_key = settings.get_openai_key()
        base_url = settings.openai_base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else OpenAI()
        self.model = settings.openai_model

    def run(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        tools = self.registry.get_openai_schemas()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        iteration = 0
        final_text = ""

        while iteration < settings.max_iterations:
            iteration += 1
            call_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": settings.temperature,
            }
            if tools:
                call_kwargs["tools"] = tools
                call_kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**call_kwargs)
            message = response.choices[0].message

            if not message.tool_calls:
                final_text = message.content or ""
                break

            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                if callbacks and "on_tool_call" in callbacks:
                    callbacks["on_tool_call"](tool_name, tool_args)

                tool_result_str = self.registry.execute(tool_name, tool_args)

                if callbacks and "on_tool_result" in callbacks:
                    callbacks["on_tool_result"](tool_name, tool_result_str)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_result_str,
                })

        updated_history = list(history)
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": final_text})
        return final_text, updated_history


class MockAgentBackend(BaseAgentBackend):
    """
    Simulated intelligent tool-calling engine for testing and offline execution.
    Inspects queries, resolves intent across all 5 tools, and formats answers.
    """

    def run(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        lowered = user_message.lower()
        tool_outputs: List[str] = []
        invocations = []

        # 1. Check for Currency Conversion requests
        currency_keywords = [
            "convert", "currency", "exchange", "usd", "eur", "gbp", "jpy", "inr", "cad",
            "aud", "chf", "cny", "sgd", "dollar", "euro", "rupee", "yen", "pound", "rates"
        ]
        curr_match = re.search(r"(\$|€|£|₹|¥)?\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]{3}|\$|€|£|₹|¥)?\s*(?:to|in|into|converted to)\s*([a-zA-Z]{3}|\$|€|£|₹|¥)?", user_message, re.IGNORECASE)

        if ("convert" in lowered and ("to" in lowered or "into" in lowered)) or (any(c in lowered for c in ["usd", "eur", "gbp", "inr", "jpy"]) and any(k in lowered for k in ["rate", "exchange", "convert", "worth"])):
            # Symbol to code map
            sym_map = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY", "dollar": "USD", "dollars": "USD", "euro": "EUR", "euros": "EUR", "rupee": "INR", "rupees": "INR", "yen": "JPY", "pound": "GBP", "pounds": "GBP"}
            
            amount = 100.0
            from_curr = "USD"
            to_curr = "EUR"

            # Try extracting number
            num_match = re.search(r"(\d+(?:\.\d+)?)", user_message)
            if num_match:
                amount = float(num_match.group(1))

            # Look for 3-letter codes or symbol words
            found_codes = re.findall(r"\b([A-Z]{3})\b", user_message.upper())
            # Filter out non-currencies
            valid_codes = [c for c in found_codes if c in ["USD", "EUR", "GBP", "JPY", "INR", "CAD", "AUD", "CHF", "CNY", "SGD", "NZD", "AED", "BRL", "KRW", "MXN", "SEK", "NOK", "TRY", "ZAR", "HKD"]]

            if len(valid_codes) >= 2:
                from_curr = valid_codes[0]
                to_curr = valid_codes[1]
            elif len(valid_codes) == 1:
                # Check target or from
                if "to " + valid_codes[0].lower() in lowered or "in " + valid_codes[0].lower() in lowered:
                    to_curr = valid_codes[0]
                    from_curr = "USD"
                else:
                    from_curr = valid_codes[0]
                    to_curr = "EUR"
            else:
                # Check for currency names (rupees, euros, dollars)
                for word, code in sym_map.items():
                    if word in lowered:
                        if "to " + word in lowered or "into " + word in lowered:
                            to_curr = code
                        else:
                            from_curr = code

            invocations.append(("convert_currency", {"amount": amount, "from_currency": from_curr, "to_currency": to_curr}))

        # 2. Check for Document Reading / Summarization requests
        doc_keywords = ["document", "doc", "pdf", "file", "summarize", "summary", "highlight", "highlights", "read document", "analyze text", "article"]
        if any(k in lowered for k in doc_keywords) and not invocations:
            # Check if there is a filename or query
            file_match = re.search(r"([\w\-_]+\.(?:pdf|txt|md|csv|json))", user_message, re.IGNORECASE)
            doc_ref = file_match.group(1) if file_match else user_message
            q = user_message if file_match else None
            invocations.append(("read_document", {"document_ref": doc_ref, "query": q}))

        # 3. Check for Math / Calculation requests (if not a pure currency query)
        math_matches = re.findall(r"(\(?\d+[\d\s\+\-\*\/\^\%\.\(\)]+[\d\)]|\bsqrt\([^\)]+\)|\bsin\([^\)]+\)|\bcos\([^\)]+\)|\bfactorial\(\d+\))", user_message)
        math_keywords = ["calculate", "compute", "what is", "math", "+", "*", "/", "^", "sqrt", "factorial"]

        if (any(kw in lowered for kw in math_keywords) or math_matches) and not any(inv[0] == "convert_currency" for inv in invocations):
            expr = user_message
            for prefix in ["calculate", "compute", "what is", "evaluate", "solve", "math:"]:
                if prefix in lowered:
                    idx = lowered.find(prefix) + len(prefix)
                    expr = user_message[idx:].strip().rstrip("?").rstrip(".")
                    break

            expr = re.sub(r"^(the\s+)?(value|result|sum|difference|product|quotient)\s+(of|for|is)\s+", "", expr, flags=re.IGNORECASE).strip()

            if math_matches:
                best_match = max(math_matches, key=len).strip()
                if not expr or any(w in expr.lower() for w in ["value", "what", "find", "is", "for", "the"]):
                    expr = best_match

            if "weather" in expr.lower():
                expr = re.sub(r"(and\s+)?(what('?s| is) the weather.*)", "", expr, flags=re.IGNORECASE).strip()

            if expr and any(char.isdigit() for char in expr):
                invocations.append(("calculate", {"expression": expr}))

        # 4. Check for Weather requests
        if "weather" in lowered or "temperature" in lowered or "forecast" in lowered or "rain" in lowered:
            loc_match = re.search(r"(?:weather\s+(?:in|for|at)|temperature\s+(?:in|for|at)|(?:in|for|at))\s+([a-zA-Z\s,]+?)(?:\?|$|\s+and|\s+with|\s+what)", user_message, re.IGNORECASE)
            raw_loc = loc_match.group(1).strip() if loc_match else "Tokyo"
            clean_loc = re.sub(r"^(is|the|weather|current|temperature)\s+", "", raw_loc, flags=re.IGNORECASE).strip()
            location = clean_loc or "Tokyo"
            unit = "fahrenheit" if "fahrenheit" in lowered or "°f" in lowered else "celsius"
            invocations.append(("get_weather", {"location": location, "unit": unit}))

        # 5. Check for Search / General Knowledge requests
        if not invocations or ("search" in lowered or "who is" in lowered or "who was" in lowered or "what happened" in lowered or "news" in lowered or "find" in lowered or "latest" in lowered):
            if not invocations:
                search_query = user_message
                for prefix in ["search for", "search", "find out", "find information about", "who is", "what is"]:
                    if prefix in lowered:
                        idx = lowered.find(prefix) + len(prefix)
                        search_query = user_message[idx:].strip().rstrip("?").rstrip(".")
                        break
                invocations.append(("search_web", {"query": search_query}))

        # Execute identified tools
        for tool_name, args in invocations:
            if callbacks and "on_tool_call" in callbacks:
                callbacks["on_tool_call"](tool_name, args)

            output = self.registry.execute(tool_name, args)
            tool_outputs.append(output)

            if callbacks and "on_tool_result" in callbacks:
                callbacks["on_tool_result"](tool_name, output)

        # Synthesize final response
        summary_lines = [
            "Based on the analysis of your request, here is the verified information:\n"
        ]
        for out in tool_outputs:
            summary_lines.append(out)

        final_text = "\n\n".join(summary_lines)
        updated_history = list(history)
        updated_history.append({"role": "user", "content": user_message})
        updated_history.append({"role": "assistant", "content": final_text})
        return final_text, updated_history


class ToolAgent:
    """
    Main orchestration class for the Tool-Calling AI Assistant.
    Maintains conversational memory, registers default tools, and routes execution backends.
    """

    def __init__(self, provider: Optional[str] = None):
        self.registry = ToolRegistry()
        self._register_default_tools()

        self.provider_name = (provider or settings.get_effective_provider()).lower()
        self.history: List[Dict[str, Any]] = []

        self.backends: List[Tuple[str, BaseAgentBackend]] = []
        self._init_backend_chain(self.provider_name)

    def _register_default_tools(self):
        """Registers the 5 core built-in tools."""
        self.registry.register(calculate, name="calculate")
        self.registry.register(convert_currency, name="convert_currency")
        self.registry.register(read_document, name="read_document")
        self.registry.register(get_weather, name="get_weather")
        self.registry.register(search_web, name="search_web")

    def register_tool(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """Allows dynamically extending the agent with custom Python tools."""
        self.registry.register(func, name=name, description=description)

    def _init_backend_chain(self, primary_provider: str):
        """Constructs an ordered chain of backends for automatic failover."""
        providers_order = []
        if primary_provider in ("gemini", "openai", "mock"):
            providers_order.append(primary_provider)

        for p in ["gemini", "openai", "mock"]:
            if p not in providers_order:
                providers_order.append(p)

        self.backends = []
        for p in providers_order:
            backend = self._create_backend(p)
            if backend:
                self.backends.append((p, backend))

    def _create_backend(self, provider_name: str) -> Optional[BaseAgentBackend]:
        """Instantiates backend instance for a given provider name."""
        try:
            if provider_name == "gemini":
                return GeminiAgentBackend(self.registry)
            elif provider_name == "openai":
                return OpenAIAgentBackend(self.registry)
            elif provider_name == "mock":
                return MockAgentBackend(self.registry)
        except Exception as e:
            logger.warning(f"Could not initialize backend for '{provider_name}': {e}")
            return None
        return None

    def chat(self, user_message: str, callbacks: Optional[Dict[str, Callable]] = None) -> str:
        """
        Executes a multi-turn conversation step with the agent.
        Features automatic failover across backend providers.
        """
        last_error = None

        for idx, (p_name, backend) in enumerate(self.backends):
            try:
                response_text, new_history = backend.run(
                    user_message=user_message,
                    history=self.history,
                    callbacks=callbacks,
                )
                self.history = new_history
                self.provider_name = p_name
                return response_text
            except Exception as e:
                last_error = e
                logger.error(f"Provider '{p_name}' encountered error: {e}")

                if idx + 1 < len(self.backends):
                    next_provider_name = self.backends[idx + 1][0]
                    if callbacks and "on_provider_fallback" in callbacks:
                        callbacks["on_provider_fallback"](p_name, next_provider_name, str(e))
                continue

        error_msg = f"All provider backends failed. Last error: {str(last_error)}"
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": error_msg})
        return error_msg

    def clear_history(self):
        """Resets conversation memory."""
        self.history = []
