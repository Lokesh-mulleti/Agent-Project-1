"""
Calculator tool for mathematical and arithmetic evaluations.
Uses safe AST parsing to prevent arbitrary code execution.
"""

import ast
import math
import operator
import re
from typing import Any, Dict, Union


class SafeMathEvaluator(ast.NodeVisitor):
    """
    Safely evaluates mathematical expressions parsed into an AST.
    Restricts operations to predefined arithmetic operators and safe math functions.
    """

    ALLOWED_OPERATORS: Dict[type, Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.BitXor: operator.pow,  # Support '^' as power (e.g., 2^3)
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    ALLOWED_FUNCTIONS: Dict[str, Any] = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "log": math.log,
        "log2": math.log2,
        "log10": math.log10,
        "exp": math.exp,
        "abs": abs,
        "round": round,
        "floor": math.floor,
        "ceil": math.ceil,
        "factorial": math.factorial,
        "gcd": math.gcd,
        "lcm": math.lcm if hasattr(math, "lcm") else (lambda a, b: abs(a * b) // math.gcd(a, b)),
        "degrees": math.degrees,
        "radians": math.radians,
    }

    ALLOWED_CONSTANTS: Dict[str, Union[int, float]] = {
        "pi": math.pi,
        "PI": math.pi,
        "e": math.e,
        "E": math.e,
        "tau": math.tau,
        "TAU": math.tau,
        "inf": math.inf,
    }

    def visit_BinOp(self, node: ast.BinOp) -> Union[int, float]:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)

        if op_type not in self.ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division or modulo by zero is not allowed.")

        return self.ALLOWED_OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Union[int, float]:
        operand = self.visit(node.operand)
        op_type = type(node.op)

        if op_type not in self.ALLOWED_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")

        return self.ALLOWED_OPERATORS[op_type](operand)

    def visit_Constant(self, node: ast.Constant) -> Union[int, float]:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Invalid constant type: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name) -> Union[int, float]:
        if node.id in self.ALLOWED_CONSTANTS:
            return self.ALLOWED_CONSTANTS[node.id]
        raise ValueError(f"Undefined variable or constant: '{node.id}'")

    def visit_Call(self, node: ast.Call) -> Union[int, float]:
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only standard function calls are permitted.")

        func_name = node.func.id
        if func_name not in self.ALLOWED_FUNCTIONS:
            raise ValueError(f"Unsupported function: '{func_name}'")

        args = [self.visit(arg) for arg in node.args]
        return self.ALLOWED_FUNCTIONS[func_name](*args)

    def generic_visit(self, node: ast.AST):
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression and returns the calculated result.

    Supported operations:
    - Arithmetic: +, -, *, /, //, %, ** (or ^)
    - Functions: sqrt(), sin(), cos(), tan(), log(), log10(), exp(), abs(), round(), floor(), ceil(), factorial()
    - Constants: pi, e, tau

    Args:
        expression: The mathematical expression string to evaluate (e.g. "(15 * 4) + sqrt(144)").

    Returns:
        A string representation of the calculation result or error details.
    """
    if not expression or not expression.strip():
        return "Error: Expression cannot be empty."

    # Clean expression and handle common syntax variants
    clean_expr = expression.strip()
    # Strip trailing punctuation like '?', '=', '.'
    clean_expr = clean_expr.rstrip("?=. ")

    # Strip conversational prefixes if passed directly to calculator
    prefix_patterns = [
        r"^(what\s+is\s+)?(the\s+)?(value|result|sum|difference|product|quotient|calculation)\s+(of|for|is)\s+",
        r"^(calculate|compute|evaluate|solve)\s+(the\s+)?(value\s+of|value\s+for|result\s+of)?\s*",
    ]
    for pattern in prefix_patterns:
        clean_expr = re.sub(pattern, "", clean_expr, flags=re.IGNORECASE).strip()

    # Replace common symbol variations
    clean_expr = clean_expr.replace("×", "*").replace("÷", "/").replace("^", "**")

    try:
        try:
            parsed_ast = ast.parse(clean_expr, mode="eval")
        except SyntaxError:
            # Fallback: attempt to isolate inner math expression if surrounded by extra words
            match = re.search(r"(\(?\d+[\d\s\+\-\*\/\^\%\.\(\)\w,]+\)?)", clean_expr)
            if match:
                clean_expr = match.group(1).strip()
                parsed_ast = ast.parse(clean_expr, mode="eval")
            else:
                raise

        evaluator = SafeMathEvaluator()
        result = evaluator.visit(parsed_ast.body)

        # Format result cleanly
        if isinstance(result, float):
            if result.is_integer():
                formatted_result = str(int(result))
            else:
                formatted_result = f"{result:.8f}".rstrip("0").rstrip(".")
        else:
            formatted_result = str(result)

        return f"Result: {formatted_result} (from: {expression})"

    except ZeroDivisionError:
        return f"Math Error: Division by zero in expression '{expression}'"
    except (ValueError, SyntaxError, TypeError) as e:
        return f"Calculation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"
