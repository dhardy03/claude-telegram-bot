"""
CLI chat interface — talk to Claude directly from PowerShell.
Claude can read, write, and edit files on your machine and run shell commands.

Commands:
  /clear    clear conversation history
  /exit     quit
  /help     show commands
  /cwd      show current working directory
  /cd <path>  change working directory
"""

import os
import subprocess
from dotenv import load_dotenv
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.rule import Rule

load_dotenv()

console = Console()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ---- tool definitions ----

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the full contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating it if it doesn't exist or overwriting it if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Replace an exact string in a file with new content. The old_string must match exactly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "old_string": {"type": "string", "description": "The exact text to find and replace"},
                "new_string": {"type": "string", "description": "The replacement text"}
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "list_directory",
        "description": "List the files and subdirectories at a given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list (defaults to current directory)"}
            },
            "required": []
        }
    },
    {
        "name": "run_command",
        "description": "Run a shell command and return its output. Always asks the user for confirmation first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"}
            },
            "required": ["command"]
        }
    }
]


# ---- tool execution ----

def execute_tool(name: str, inputs: dict) -> str:
    if name == "read_file":
        path = inputs["path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: file not found: {path}"
        except Exception as e:
            return f"Error reading file: {e}"

    elif name == "write_file":
        path = inputs["path"]
        content = inputs["content"]
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to {path}"
        except Exception as e:
            return f"Error writing file: {e}"

    elif name == "edit_file":
        path = inputs["path"]
        old_string = inputs["old_string"]
        new_string = inputs["new_string"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_string not in content:
                return f"Error: the specified text was not found in {path}"
            new_content = content.replace(old_string, new_string, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"Successfully edited {path}"
        except FileNotFoundError:
            return f"Error: file not found: {path}"
        except Exception as e:
            return f"Error editing file: {e}"

    elif name == "list_directory":
        path = inputs.get("path", ".")
        try:
            items = sorted(os.listdir(path))
            lines = []
            for item in items:
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    lines.append(f"  📁 {item}/")
                else:
                    size = os.path.getsize(full)
                    lines.append(f"  📄 {item}  ({size:,} bytes)")
            return "\n".join(lines) if lines else "(empty directory)"
        except FileNotFoundError:
            return f"Error: directory not found: {path}"
        except Exception as e:
            return f"Error listing directory: {e}"

    elif name == "run_command":
        command = inputs["command"]
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd()
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n(exit code {result.returncode})"
            return output.strip() if output.strip() else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 60 seconds"
        except Exception as e:
            return f"Error running command: {e}"

    return f"Error: unknown tool {name}"


# ---- tool call display ----

TOOL_ICONS = {
    "read_file": "📖",
    "write_file": "✏️ ",
    "edit_file": "🔧",
    "list_directory": "📂",
    "run_command": "⚡",
}

def show_tool_call(name: str, inputs: dict):
    icon = TOOL_ICONS.get(name, "🔨")
    if name == "read_file":
        detail = inputs.get("path", "")
    elif name == "write_file":
        detail = f"{inputs.get('path', '')}  ({len(inputs.get('content', ''))} chars)"
    elif name == "edit_file":
        detail = inputs.get("path", "")
    elif name == "list_directory":
        detail = inputs.get("path", ".")
    elif name == "run_command":
        detail = inputs.get("command", "")
    else:
        detail = str(inputs)

    console.print(f"  {icon} [bold dim]{name}[/bold dim]  [dim]{detail}[/dim]")


# ---- agentic loop ----

def run_agent(history: list) -> str:
    """Send history to Claude, handle tool calls, return final text reply."""

    system = (
        f"You are a helpful coding assistant with access to the user's filesystem and shell.\n"
        f"Current working directory: {os.getcwd()}\n\n"
        "You can read, write, and edit files and run shell commands. "
        "Be concise. Prefer edit_file over rewriting whole files when making small changes. "
        "Always explain what you're about to do before calling tools."
    )

    while True:
        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=history
            )

        history.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # extract final text
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        elif response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                # print any text Claude says before calling tools
                if hasattr(block, "text") and block.text.strip():
                    console.print()
                    console.print(Text("Claude", style="bold magenta"), end="  ")
                    console.print()
                    console.print(Markdown(block.text))

                if block.type == "tool_use":
                    show_tool_call(block.name, block.input)

                    # require confirmation before running shell commands
                    if block.name == "run_command":
                        console.print()
                        approved = Confirm.ask(
                            f"  [yellow]Run:[/yellow] [bold]{block.input['command']}[/bold]",
                            default=True
                        )
                        if not approved:
                            result = "User declined to run this command."
                        else:
                            result = execute_tool(block.name, block.input)
                    else:
                        result = execute_tool(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            console.print()
            history.append({"role": "user", "content": tool_results})

        else:
            break

    return ""


# ---- main chat loop ----

def show_banner():
    console.print(Panel.fit(
        "[bold cyan]AI Bot — CLI[/bold cyan]\n"
        f"[dim]cwd: {os.getcwd()}[/dim]\n"
        "[dim]Type [bold]/help[/bold] for commands[/dim]",
        border_style="cyan"
    ))
    console.print()


def show_help():
    console.print(Panel(
        "[bold]/clear[/bold]       clear conversation history\n"
        "[bold]/exit[/bold]        quit\n"
        "[bold]/help[/bold]        show this message\n"
        "[bold]/cwd[/bold]         show current working directory\n"
        "[bold]/cd <path>[/bold]   change working directory",
        title="Commands",
        border_style="dim"
    ))
    console.print()


def chat():
    show_banner()
    history = []

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/dim]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            args = user_input.split(maxsplit=1)[1] if " " in user_input else ""

            if cmd == "/exit":
                console.print("[dim]Bye.[/dim]")
                break
            elif cmd == "/clear":
                history = []
                console.print("[dim]Conversation cleared.[/dim]\n")
            elif cmd == "/help":
                show_help()
            elif cmd == "/cwd":
                console.print(f"[dim]{os.getcwd()}[/dim]\n")
            elif cmd == "/cd":
                if args:
                    try:
                        os.chdir(args)
                        console.print(f"[dim]Now in {os.getcwd()}[/dim]\n")
                    except Exception as e:
                        console.print(f"[red]{e}[/red]\n")
                else:
                    console.print("[red]Usage: /cd <path>[/red]\n")
            else:
                console.print(f"[red]Unknown command:[/red] {user_input}\n")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            reply = run_agent(history)
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}\n")
            history.pop()
            continue

        if reply:
            console.print()
            console.print(Text("Claude", style="bold magenta"), end="  ")
            console.print(Text(f"[{len(history) // 2} turns]", style="dim"))
            console.print(Markdown(reply))
            console.print()


if __name__ == "__main__":
    chat()
