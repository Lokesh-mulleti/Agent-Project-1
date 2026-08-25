"""
Unit tests for the AST-based safe calculator tool.
"""

import pytest
from app.tools.calculator import calculate, SafeMathEvaluator


def test_basic_arithmetic():
    assert "Result: 7" in calculate("3 + 4")
    assert "Result: 15" in calculate("20 - 5")
    assert "Result: 42" in calculate("6 * 7")
    assert "Result: 4" in calculate("20 / 5")
    assert "Result: 3" in calculate("10 // 3")
    assert "Result: 1" in calculate("10 % 3")


def test_operator_precedence_and_parentheses():
    assert "Result: 14" in calculate("2 + 3 * 4")
    assert "Result: 20" in calculate("(2 + 3) * 4")
    assert "Result: 25" in calculate("((10 - 5) * 5)")


def test_powers_and_exponents():
    assert "Result: 8" in calculate("2 ** 3")
    assert "Result: 16" in calculate("2 ^ 4")


def test_math_functions():
    assert "Result: 12" in calculate("sqrt(144)")
    assert "Result: 120" in calculate("factorial(5)")
    assert "Result: 5" in calculate("abs(-5)")
    assert "Result: 3" in calculate("floor(3.9)")
    assert "Result: 4" in calculate("ceil(3.1)")
    assert "Result: 4" in calculate("round(3.7)")


def test_math_constants():
    assert "Result: 3.14159265" in calculate("pi")
    assert "Result: 6.28318531" in calculate("2 * pi")
    assert "Result: 2.71828183" in calculate("e")


def test_division_by_zero():
    res = calculate("10 / 0")
    assert "Math Error: Division by zero" in res


def test_modulo_by_zero():
    res = calculate("10 % 0")
    assert "Math Error: Division by zero" in res


def test_empty_and_invalid_expressions():
    assert "Error: Expression cannot be empty" in calculate("")
    assert "Error: Expression cannot be empty" in calculate("   ")
    assert "Calculation Error" in calculate("3 + ")


def test_security_ast_isolation():
    """Ensure safe evaluator rejects malicious calls or arbitrary code injection."""
    res = calculate("__import__('os').system('ls')")
    assert "Calculation Error" in res

    res2 = calculate("open('/etc/passwd')")
    assert "Calculation Error" in res2


def test_natural_language_sanitization():
    """Ensure calculator handles queries with conversational prefixes and punctuation."""
    assert "Result: 385" in calculate("the value for (192 + 193)")
    assert "Result: 385" in calculate("what is the value of 192 + 193?")
    assert "Result: 385" in calculate("calculate the sum of (192 + 193) =")
    assert "Result: 50" in calculate("result of 25 * 2")
