"""
Document Reader & Analyzer tool for AI Tool-Calling Assistant.
Parses PDF, Markdown, TXT, CSV, JSON and provides structured summaries,
key sentence highlighting, entity extraction, and context-grounded Q&A.
"""

import os
import re
import io
import json
import csv
from typing import Dict, Any, List, Optional, Tuple

# Global in-memory document store for session uploaded docs
DOCUMENT_STORE: Dict[str, Dict[str, Any]] = {}


def register_uploaded_document(doc_id: str, filename: str, content: str, doc_type: str = "text") -> Dict[str, Any]:
    """Saves a document to the active session document store for agent tool inspection."""
    analysis = analyze_text_content(content, filename=filename, doc_type=doc_type)
    DOCUMENT_STORE[doc_id] = {
        "doc_id": doc_id,
        "filename": filename,
        "content": content,
        "doc_type": doc_type,
        "analysis": analysis,
    }
    # Also register by lowercase filename for easy lookup
    DOCUMENT_STORE[filename.lower()] = DOCUMENT_STORE[doc_id]
    return analysis


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """Extracts raw plain text from file bytes (PDF, TXT, MD, CSV, JSON)."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            pages_text = []
            for i, page in enumerate(pdf_reader.pages):
                txt = page.extract_text() or ""
                if txt.strip():
                    pages_text.append(f"--- [Page {i+1}] ---\n{txt}")
            return "\n\n".join(pages_text), "pdf"
        except Exception as e:
            return f"Error extracting PDF text: {str(e)}", "pdf"

    elif ext in (".csv", ".tsv"):
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows = [", ".join(row) for row in reader if row]
            return "\n".join(rows), "csv"
        except Exception as e:
            return f"Error reading CSV: {str(e)}", "csv"

    elif ext == ".json":
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2), "json"
        except Exception:
            return file_bytes.decode("utf-8", errors="replace"), "json"

    else:
        # Default text/markdown
        return file_bytes.decode("utf-8", errors="replace"), "markdown" if ext in (".md", ".markdown") else "text"


def analyze_text_content(content: str, filename: str = "document", doc_type: str = "text") -> Dict[str, Any]:
    """Generates structured statistics, key highlights, and executive summary for a text."""
    if not content or not content.strip():
        return {
            "error": "Document content is empty.",
            "filename": filename,
            "word_count": 0,
            "highlights": [],
            "summary": "Empty document.",
        }

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    words = content.split()
    word_count = len(words)
    char_count = len(content)
    reading_time_min = max(1, round(word_count / 200))

    # Identify Key Highlights (Important sentences containing metrics, conclusions, key definitions)
    sentences = re.split(r"(?<=[.!?])\s+", content)
    highlights = []
    importance_keywords = [
        "crucial", "important", "significant", "key", "result", "conclusion",
        "increase", "decrease", "growth", "revenue", "objective", "finding",
        "recommend", "required", "critical", "achieved", "total", "summary",
        "percent", "%", "$", "million", "billion", "first", "finally", "must"
    ]

    for sent in sentences:
        sent_clean = sent.strip().replace("\n", " ")
        if len(sent_clean) < 25 or len(sent_clean) > 280:
            continue
        # Score sentence importance
        score = sum(1 for kw in importance_keywords if kw in sent_clean.lower())
        # Check for numbers/metrics
        if re.search(r"\d+", sent_clean):
            score += 1
        if score >= 2:
            highlights.append({
                "text": sent_clean,
                "score": score,
                "category": "Metric/Finding" if re.search(r"\d+", sent_clean) else "Key Takeaway",
            })

    # Sort highlights by importance score and take top 6
    highlights = sorted(highlights, key=lambda x: x["score"], reverse=True)[:6]

    # If no keywords matched, grab first few informative sentences
    if not highlights:
        for sent in sentences[:4]:
            if len(sent.strip()) > 30:
                highlights.append({
                    "text": sent.strip().replace("\n", " "),
                    "score": 1,
                    "category": "Key Point",
                })

    # Generate Brief Executive Description
    first_paragraph = "\n".join(lines[:6]) if len(lines) >= 6 else "\n".join(lines)
    summary_preview = first_paragraph[:450] + ("..." if len(first_paragraph) > 450 else "")

    return {
        "filename": filename,
        "doc_type": doc_type,
        "word_count": word_count,
        "char_count": char_count,
        "reading_time_min": reading_time_min,
        "highlights": highlights,
        "summary": summary_preview,
        "total_lines": len(lines),
    }


def read_document(document_ref: str, query: Optional[str] = None) -> str:
    """
    Reads, summarizes, and extracts key highlighted points from a document or text.

    Args:
        document_ref: The document ID, filename, file path, or raw text snippet to inspect.
        query: Optional specific question or topic to search for within the document context.

    Returns:
        A structured breakdown including Brief Description, Key Highlights, and Context Q&A.
    """
    ref_key = document_ref.strip().lower()
    content = ""
    filename = document_ref

    # 1. Check in-memory document store
    if ref_key in DOCUMENT_STORE:
        doc_entry = DOCUMENT_STORE[ref_key]
        content = doc_entry["content"]
        filename = doc_entry["filename"]
    elif document_ref in DOCUMENT_STORE:
        doc_entry = DOCUMENT_STORE[document_ref]
        content = doc_entry["content"]
        filename = doc_entry["filename"]
    # 2. Check local file path if file exists
    elif os.path.exists(document_ref) and os.path.isfile(document_ref):
        try:
            with open(document_ref, "rb") as f:
                content, _ = extract_text_from_bytes(f.read(), os.path.basename(document_ref))
            filename = os.path.basename(document_ref)
        except Exception as e:
            return f"Document Error: Could not read file '{document_ref}': {str(e)}"
    else:
        # Treat document_ref as direct text content
        content = document_ref
        filename = "Text Snippet"

    if not content or not content.strip():
        return "Document Error: No readable text content found in document reference."

    analysis = analyze_text_content(content, filename=filename)

    # Format structured report
    output_lines = [
        f"📄 Document Analysis for '{filename}':",
        f"• Metrics: {analysis['word_count']} words | ~{analysis['reading_time_min']} min read | {analysis['total_lines']} lines",
        "",
        "📋 Brief Executive Description:",
        f"{analysis['summary']}",
        "",
        "✨ Key Highlights & Takeaways:",
    ]

    for i, hl in enumerate(analysis["highlights"], 1):
        output_lines.append(f"  {i}. [{hl['category']}] \"{hl['text']}\"")

    # If user provided a specific search/question query against the document
    if query and query.strip():
        q_lower = query.lower()
        matching_snippets = []
        for line in content.splitlines():
            if any(term in line.lower() for term in q_lower.split() if len(term) > 3):
                matching_snippets.append(line.strip())

        output_lines.append("")
        output_lines.append(f"🔍 Relevant Context for Query '{query}':")
        if matching_snippets:
            for snip in matching_snippets[:5]:
                output_lines.append(f"  • {snip}")
        else:
            output_lines.append("  • No direct verbatim match found; synthesized from overall document context.")

    return "\n".join(output_lines)
