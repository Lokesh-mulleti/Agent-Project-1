"""
Configuration module for AI Tool-Calling Assistant.
Loads environment variables and application parameters safely.
"""

import os
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration and environment settings."""

    # LLM Provider selection
    llm_provider: Literal["gemini", "openai", "mock"] = Field(
        default="gemini",
        description="LLM provider backend ('gemini', 'openai', or 'mock')",
    )

    # Google Gemini Settings
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="API key for Google Gemini",
    )
    gemini_model: str = Field(
        default="gemini-3.7-flash",
        description="Gemini model name to use",
    )

    # OpenAI / OpenAI-compatible Settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="API key for OpenAI or compatible provider",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier",
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom base URL for OpenAI-compatible services (e.g. Ollama, Groq, OpenRouter)",
    )

    # Web Server Settings
    server_host: str = Field(
        default="0.0.0.0",
        description="Server bind host",
    )
    server_port: int = Field(
        default=8000,
        description="Server bind port",
    )

    # Agent execution parameters
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for LLM responses",
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum tool calling loop iterations before terminating",
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable verbose debug logging for tool calls and raw LLM responses",
    )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_gemini_key(self) -> Optional[str]:
        key = self.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if key and key.strip() and "your_gemini_api_key" not in key:
            return key.strip()
        return None

    def get_openai_key(self) -> Optional[str]:
        key = self.openai_api_key or os.getenv("OPENAI_API_KEY")
        if key and key.strip() and "your_openai_api_key" not in key:
            return key.strip()
        return None

    def get_effective_provider(self) -> str:
        """Determines the active provider based on configuration and available keys."""
        provider = self.llm_provider.lower().strip()
        gemini_key = self.get_gemini_key()
        openai_key = self.get_openai_key()

        # If user explicitly requested OpenAI and key is present
        if provider == "openai" and openai_key:
            return "openai"

        # If user explicitly requested Gemini and key is present
        if provider == "gemini" and gemini_key:
            return "gemini"

        # Smart Auto-Detection if preferred provider has no key:
        if openai_key and not gemini_key:
            return "openai"
        elif gemini_key and not openai_key:
            return "gemini"
        elif openai_key and gemini_key:
            return provider if provider in ("openai", "gemini") else "gemini"

        return "mock"


# Singleton instance
settings = Settings()
