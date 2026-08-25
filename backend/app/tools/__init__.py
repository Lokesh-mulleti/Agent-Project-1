"""
Tools package for AI Tool-Calling Assistant.
Exports all registered agent execution tools.
"""

from app.tools.calculator import calculate
from app.tools.currency import convert_currency
from app.tools.doc_reader import read_document, register_uploaded_document
from app.tools.weather import get_weather
from app.tools.search import search_web

__all__ = [
    "calculate",
    "convert_currency",
    "read_document",
    "register_uploaded_document",
    "get_weather",
    "search_web",
]
