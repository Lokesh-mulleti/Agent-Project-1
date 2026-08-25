"""
FastAPI Web Server for AI Tool-Calling Assistant.
Provides REST and Server-Sent Events (SSE) streaming endpoints,
document upload parsing, tool execution playground, and static UI delivery.
"""

import os
import sys
import json
import asyncio
import uuid
import time

# Ensure backend directory is in Python path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.agent.agent import ToolAgent
from app.tools.doc_reader import register_uploaded_document, extract_text_from_bytes

# Initialize FastAPI App
app = FastAPI(
    title="AI Tool-Calling Assistant API",
    description="Autonomous Multi-Provider AI Agent with Real-Time Dynamic Function Calling",
    version="2.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global persistent agent instance for the session
session_agent = ToolAgent()

# Determine frontend static files directory
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))


# Request / Response Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    provider: Optional[str] = Field(None, description="Optional provider override (gemini, openai, mock)")
    model: Optional[str] = Field(None, description="Optional model override")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Dictionary of arguments")


class SettingsUpdateRequest(BaseModel):
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_base_url: Optional[str] = None
    temperature: Optional[float] = None


@app.get("/api/health")
async def health_check():
    """Health check and provider status."""
    return {
        "status": "online",
        "version": "2.0.0",
        "primary_provider": session_agent.provider_name,
        "effective_provider": settings.get_effective_provider(),
        "registered_tools": session_agent.registry.list_names(),
        "total_messages": len(session_agent.history),
    }


@app.get("/api/settings")
async def get_settings():
    """Returns current runtime configurations and provider status."""
    return {
        "llm_provider": session_agent.provider_name,
        "configured_provider": settings.llm_provider,
        "gemini_configured": bool(settings.get_gemini_key()),
        "gemini_model": settings.gemini_model,
        "openai_configured": bool(settings.get_openai_key()),
        "openai_model": settings.openai_model,
        "openai_base_url": settings.openai_base_url,
        "temperature": settings.temperature,
        "max_iterations": settings.max_iterations,
        "available_models": {
            "gemini": ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "mock": ["Built-in Heuristic Engine (Offline)"],
        },
    }


@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Updates runtime settings and refreshes backend agent chain."""
    if req.llm_provider:
        settings.llm_provider = req.llm_provider.lower().strip()
    if req.gemini_api_key is not None:
        settings.gemini_api_key = req.gemini_api_key.strip()
    if req.gemini_model:
        settings.gemini_model = req.gemini_model.strip()
    if req.openai_api_key is not None:
        settings.openai_api_key = req.openai_api_key.strip()
    if req.openai_model:
        settings.openai_model = req.openai_model.strip()
    if req.openai_base_url is not None:
        settings.openai_base_url = req.openai_base_url.strip() if req.openai_base_url else None
    if req.temperature is not None:
        settings.temperature = req.temperature

    # Reinitialize backend chain
    session_agent._init_backend_chain(settings.llm_provider)
    session_agent.provider_name = settings.get_effective_provider()

    return {
        "status": "success",
        "message": "Settings updated successfully",
        "active_provider": session_agent.provider_name,
    }


@app.get("/api/tools")
async def list_tools():
    """Returns detailed documentation and JSON schemas for all registered tools."""
    schemas = session_agent.registry.get_openai_schemas()
    return {
        "total_tools": len(schemas),
        "tools": [s["function"] for s in schemas],
    }


@app.post("/api/tools/execute")
async def execute_tool_direct(req: ToolExecuteRequest):
    """Directly executes an individual tool with arguments for testing in UI Playground."""
    start_time = time.time()
    result = session_agent.registry.execute(req.tool_name, req.arguments)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    return {
        "tool_name": req.tool_name,
        "arguments": req.arguments,
        "result": result,
        "duration_ms": duration_ms,
    }


@app.post("/api/upload-doc")
async def upload_document(
    file: UploadFile = File(...),
    doc_id: Optional[str] = Form(None),
):
    """Uploads a document (PDF, TXT, MD, CSV, JSON) and extracts structured analysis and highlights."""
    try:
        content_bytes = await file.read()
        filename = file.filename or "uploaded_file"
        doc_id = doc_id or f"doc_{uuid.uuid4().hex[:8]}"

        raw_text, doc_type = extract_text_from_bytes(content_bytes, filename)
        analysis = register_uploaded_document(doc_id=doc_id, filename=filename, content=raw_text, doc_type=doc_type)

        return {
            "status": "success",
            "doc_id": doc_id,
            "filename": filename,
            "doc_type": doc_type,
            "analysis": analysis,
            "raw_text_preview": raw_text[:1200] + ("..." if len(raw_text) > 1200 else ""),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process document: {str(e)}")


@app.post("/api/clear")
async def clear_chat_history():
    """Clears conversational memory."""
    session_agent.clear_history()
    return {"status": "success", "message": "Conversation history reset."}


@app.post("/api/chat")
async def chat_streaming(req: ChatRequest):
    """
    Executes a chat query with Server-Sent Events (SSE) streaming.
    Streams tool calls, intermediate results, provider failovers, and final answer.
    """
    async def event_generator():
        # Setup event queue for asynchronous callback delivery
        loop = asyncio.get_event_loop()
        event_queue = asyncio.Queue()

        def on_tool_call(name: str, args: Dict[str, Any]):
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                {
                    "type": "tool_call",
                    "tool": name,
                    "args": args,
                    "timestamp": time.time(),
                }
            )

        def on_tool_result(name: str, result: str):
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                {
                    "type": "tool_result",
                    "tool": name,
                    "result": result,
                    "timestamp": time.time(),
                }
            )

        def on_provider_fallback(failed_p: str, next_p: str, error_msg: str):
            loop.call_soon_threadsafe(
                event_queue.put_nowait,
                {
                    "type": "provider_fallback",
                    "failed_provider": failed_p,
                    "next_provider": next_p,
                    "error": error_msg,
                    "timestamp": time.time(),
                }
            )

        callbacks = {
            "on_tool_call": on_tool_call,
            "on_tool_result": on_tool_result,
            "on_provider_fallback": on_provider_fallback,
        }

        # Override provider if specified in request
        if req.provider and req.provider != session_agent.provider_name:
            session_agent.provider_name = req.provider.lower()
            session_agent._init_backend_chain(session_agent.provider_name)

        # Run agent in background executor
        start_time = time.time()
        chat_future = loop.run_in_executor(
            None,
            lambda: session_agent.chat(req.message, callbacks=callbacks),
        )

        # Stream queued events as they arrive
        while not chat_future.done() or not event_queue.empty():
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                continue

        # Final response
        final_answer = await chat_future
        total_latency_ms = round((time.time() - start_time) * 1000, 2)

        completion_event = {
            "type": "final_response",
            "content": final_answer,
            "provider": session_agent.provider_name,
            "latency_ms": total_latency_ms,
        }
        yield f"data: {json.dumps(completion_event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Mount frontend static directory if exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
