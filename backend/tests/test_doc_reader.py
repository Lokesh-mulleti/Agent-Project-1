"""
Unit tests for the document reader and analyzer tool.
"""

import pytest
from app.tools.doc_reader import (
    analyze_text_content,
    read_document,
    register_uploaded_document,
    extract_text_from_bytes,
)


def test_empty_content_analysis():
    res = analyze_text_content("")
    assert "error" in res


def test_text_analysis_and_highlighting():
    sample_text = """
    Q3 Financial and Strategic Report.
    The company achieved a critical revenue increase of 45% reaching $120 million.
    Our primary objective was expanding into European markets.
    Customer retention grew by 18% which is a significant milestone for our platform.
    We recommend increasing research and development expenditure in AI by 25%.
    """
    analysis = analyze_text_content(sample_text, filename="q3_report.txt")
    assert analysis["word_count"] > 20
    assert len(analysis["highlights"]) > 0
    assert any("45%" in hl["text"] or "revenue" in hl["text"].lower() for hl in analysis["highlights"])


def test_read_document_direct_string():
    sample = "Project Apollo was crucial. The total investment was $25 billion with 300,000 employees."
    output = read_document(sample)
    assert "Document Analysis" in output
    assert "Brief Executive Description" in output
    assert "Key Highlights" in output


def test_registered_document_lookup():
    doc_id = "test_doc_01"
    content = "Antigravity AI is a crucial next-generation autonomous coding platform."
    register_uploaded_document(doc_id, "antigravity.txt", content)

    res = read_document(doc_id)
    assert "antigravity.txt" in res
    assert "Antigravity AI" in res


def test_document_query_search():
    content = "The headquarters is located in San Francisco, California. Annual revenue reached $500 million."
    res = read_document(content, query="headquarters location")
    assert "San Francisco" in res
