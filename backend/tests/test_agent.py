"""
Unit and integration tests for ToolAgent, ToolRegistry, and execution backends.
"""

import pytest
from app.agent.agent import ToolAgent, ToolRegistry, MockAgentBackend
from app.tools.calculator import calculate
from app.tools.currency import convert_currency
from app.tools.doc_reader import read_document
from app.tools.weather import get_weather
from app.tools.search import search_web


def test_tool_registry_registration():
    registry = ToolRegistry()
    registry.register(calculate, name="calc")
    assert "calc" in registry.list_names()
    assert registry.get_tool("calc") == calculate


def test_tool_registry_schema_generation():
    registry = ToolRegistry()
    registry.register(convert_currency, name="convert_currency")
    schemas = registry.get_openai_schemas()
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "convert_currency"
    assert "amount" in schemas[0]["function"]["parameters"]["properties"]


def test_tool_registry_execution():
    registry = ToolRegistry()
    registry.register(calculate, name="calculate")
    res = registry.execute("calculate", {"expression": "5 * 5"})
    assert "Result: 25" in res


def test_mock_agent_math_query():
    agent = ToolAgent(provider="mock")
    calls = []
    callbacks = {
        "on_tool_call": lambda name, args: calls.append((name, args)),
    }

    response = agent.chat("What is 100 * 5?", callbacks=callbacks)
    assert len(calls) >= 1
    assert calls[0][0] == "calculate"
    assert "500" in response

    # Conversational / Natural language phrasing
    calls.clear()
    response2 = agent.chat("what is the value for (192 + 193)?", callbacks=callbacks)
    assert len(calls) >= 1
    assert calls[0][0] == "calculate"
    assert "385" in response2


def test_mock_agent_currency_query():
    agent = ToolAgent(provider="mock")
    calls = []
    callbacks = {
        "on_tool_call": lambda name, args: calls.append((name, args)),
    }

    response = agent.chat("Convert 500 USD to EUR", callbacks=callbacks)
    assert len(calls) >= 1
    assert calls[0][0] == "convert_currency"
    assert "EUR" in response or "Conversion" in response


def test_mock_agent_doc_reading_query():
    agent = ToolAgent(provider="mock")
    calls = []
    callbacks = {
        "on_tool_call": lambda name, args: calls.append((name, args)),
    }

    response = agent.chat("Summarize the crucial findings in report.txt", callbacks=callbacks)
    assert len(calls) >= 1
    assert calls[0][0] == "read_document"


def test_mock_agent_weather_query():
    agent = ToolAgent(provider="mock")
    calls = []
    callbacks = {
        "on_tool_call": lambda name, args: calls.append((name, args)),
    }

    response = agent.chat("What is the weather in London?", callbacks=callbacks)
    assert len(calls) >= 1
    assert calls[0][0] == "get_weather"
    assert "London" in response or "Weather" in response


def test_agent_history_and_clear():
    agent = ToolAgent(provider="mock")
    agent.chat("Compute 2 + 2")
    assert len(agent.history) == 2

    agent.chat("What is the weather in Paris?")
    assert len(agent.history) == 4

    agent.clear_history()
    assert len(agent.history) == 0


def test_agent_automatic_failover():
    agent = ToolAgent(provider="mock")

    class FailingBackend:
        def run(self, user_message, history, callbacks=None):
            raise ConnectionError("Simulated provider outage / timeout")

    agent.backends = [
        ("broken_provider", FailingBackend()),
        ("mock", MockAgentBackend(agent.registry)),
    ]
    agent.provider_name = "broken_provider"

    fallbacks = []
    callbacks = {
        "on_provider_fallback": lambda failed, next_p, err: fallbacks.append((failed, next_p, err)),
    }

    response = agent.chat("What is 50 * 4?", callbacks=callbacks)
    assert len(fallbacks) == 1
    assert fallbacks[0][0] == "broken_provider"
    assert fallbacks[0][1] == "mock"
    assert "200" in response
