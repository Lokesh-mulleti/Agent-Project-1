"""
Main unified entry point for AI Tool-Calling Assistant.
Supports Interactive Terminal UI, CLI Direct Queries, and Web Server modes.
"""

import argparse
import sys
import os

# Ensure backend directory is in Python path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.theme import Theme

from app.config import settings
from app.agent.agent import ToolAgent

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "tool": "bold magenta",
    "agent": "bold blue",
})

console = Console(theme=custom_theme, safe_box=True)


def print_banner(agent: ToolAgent):
    """Renders the startup banner and agent configuration table."""
    banner_text = """
╔═══════════════════════════════════════════════════════════════╗
║                   AI TOOL-CALLING ASSISTANT                   ║
║            Autonomous Reasoning & Execution Engine            ║
╚═══════════════════════════════════════════════════════════════╝
"""
    console.print(banner_text, style="bold cyan")

    table = Table(title="Agent Configuration", border_style="bright_blue", show_header=True)
    table.add_column("Property", style="bold white", width=22)
    table.add_column("Value", style="cyan")

    table.add_row("Primary Provider", f"[bold green]{agent.provider_name.upper()}[/bold green]")
    active_model = settings.gemini_model if agent.provider_name == "gemini" else (
        settings.openai_model if agent.provider_name == "openai" else "Built-in Heuristic Mock Engine"
    )
    table.add_row("Active Model", active_model)
    chain_str = " -> ".join(f"[bold yellow]{p.upper()}[/bold yellow]" for p, _ in agent.backends)
    table.add_row("Failover Chain", chain_str)
    table.add_row("Registered Tools", f"[magenta]{', '.join(agent.registry.list_names())}[/magenta]")
    table.add_row("Sampling Temp", str(settings.temperature))

    console.print(table)
    console.print(
        "\n[dim]Commands: '[bold white]tools[/bold white]' to list tools | '[bold white]clear[/bold white]' to reset memory | '[bold white]exit[/bold white]' to quit[/dim]\n"
    )


def print_tools_table(agent: ToolAgent):
    """Displays registered tool signatures and documentation."""
    table = Table(title="Registered Tools & Schemas", border_style="magenta", show_header=True)
    table.add_column("Tool Name", style="bold green", width=18)
    table.add_column("Description", style="white", width=42)
    table.add_column("Parameters", style="cyan", width=25)

    for schema in agent.registry.get_openai_schemas():
        fn = schema["function"]
        params = list(fn["parameters"]["properties"].keys())
        table.add_row(fn["name"], fn["description"], ", ".join(params))

    console.print(table)


def run_interactive_session(agent: ToolAgent):
    """Starts the interactive terminal chat loop."""
    print_banner(agent)

    callbacks = {
        "on_tool_call": lambda name, a: console.print(
            Panel(
                f"[bold magenta]>> Executing Tool:[/bold magenta] [bold white]{name}[/bold white]\n[cyan]Arguments:[/cyan] {a}",
                title="[bold magenta]Tool Invocation[/bold magenta]",
                border_style="magenta",
            )
        ),
        "on_tool_result": lambda name, r: console.print(
            Panel(
                f"{r}",
                title=f"[bold cyan]Result from {name}[/bold cyan]",
                border_style="cyan",
            )
        ),
        "on_provider_fallback": lambda failed_p, next_p, err: console.print(
            Panel(
                f"[bold red]✗ Primary Provider '{failed_p.upper()}' failed:[/bold red] {err[:80]}...\n"
                f"[bold green]✔ Automatically failing over to:[/bold green] [bold yellow]{next_p.upper()}[/bold yellow]",
                title="[bold yellow]Automatic Model Failover[/bold yellow]",
                border_style="yellow",
            )
        ),
    }

    while True:
        try:
            user_input = console.input("[bold green]User > [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Session ended. Goodbye![/yellow]")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("exit", "quit", "q"):
            console.print("[yellow]Exiting assistant. Goodbye![/yellow]")
            break
        elif cmd == "tools":
            print_tools_table(agent)
            continue
        elif cmd == "clear":
            agent.clear_history()
            console.print("[green]✔ Conversation history cleared.[/green]\n")
            continue
        elif cmd == "help":
            console.print(
                "[info]Type your natural language request, or commands: 'tools', 'clear', 'exit'[/info]\n"
            )
            continue

        with console.status("[bold blue]Agent reasoning and deciding actions...[/bold blue]", spinner="dots"):
            response = agent.chat(user_input, callbacks=callbacks)

        console.print(
            Panel(
                Markdown(response),
                title="[bold blue]Assistant Response[/bold blue]",
                border_style="blue",
            )
        )
        console.print()


def run_web_server(host: str = "0.0.0.0", port: int = 8000):
    """Launches the Uvicorn web server."""
    import uvicorn
    from app.server import app as fastapi_app
    console.print(
        Panel(
            f"[bold green]🚀 AI Tool-Calling Assistant Web Server Starting...[/bold green]\n\n"
            f"• [bold cyan]Local UI URL:[/bold cyan]  [link=http://localhost:{port}]http://localhost:{port}[/link]\n"
            f"• [bold cyan]API Docs:[/bold cyan]      [link=http://localhost:{port}/docs]http://localhost:{port}/docs[/link]\n"
            f"• [bold cyan]Bind Address:[/bold cyan]  {host}:{port}\n\n"
            f"[dim]Press Ctrl+C to stop the web server[/dim]",
            title="[bold blue]Web Server Launch[/bold blue]",
            border_style="bright_blue",
        )
    )
    uvicorn.run(fastapi_app, host=host, port=port)


def main():
    """CLI argument parsing and main execution dispatch."""
    parser = argparse.ArgumentParser(description="AI Tool-Calling Assistant")
    parser.add_argument(
        "-w", "--web",
        action="store_true",
        help="Launch the Web UI and FastAPI server.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=settings.server_host,
        help="Web server host (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.server_port,
        help="Web server port (default: 8000).",
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Execute a single query directly and output the answer.",
    )
    parser.add_argument(
        "-p", "--provider",
        type=str,
        choices=["gemini", "openai", "mock"],
        help="Override LLM provider backend ('gemini', 'openai', 'mock').",
    )
    parser.add_argument(
        "-m", "--mock",
        action="store_true",
        help="Force offline mock provider execution.",
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    args = parser.parse_args()

    if args.web:
        run_web_server(host=args.host, port=args.port)
        return

    provider = "mock" if args.mock else args.provider
    agent = ToolAgent(provider=provider)

    if args.query:
        # Run single query mode
        callbacks = {
            "on_tool_call": lambda name, a: console.print(f"[magenta]>> Tool Called:[/magenta] {name}({a})"),
            "on_tool_result": lambda name, r: console.print(f"[cyan]>> Result ({name}):[/cyan] {r}\n"),
            "on_provider_fallback": lambda failed_p, next_p, err: console.print(
                f"[bold yellow]⚠ Provider '{failed_p.upper()}' failed. Failing over to '{next_p.upper()}'...[/bold yellow]\n"
            ),
        }
        response = agent.chat(args.query, callbacks=callbacks)
        console.print(
            Panel(
                Markdown(response),
                title="[bold blue]Assistant Response[/bold blue]",
                border_style="blue",
            )
        )
    else:
        # Run interactive session
        run_interactive_session(agent)


if __name__ == "__main__":
    main()
