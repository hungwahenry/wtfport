# wtfport/output.py
"""
Output formatting for wtfport.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Dict, List, Any, Optional

# Create a global console instance
console = Console()

def print_process_detail(port: int, process_info: Optional[Dict[str, Any]], is_web: bool = False, log_file: Optional[str] = None):
    """Print detailed information about a process."""
    if not process_info:
        console.print(f"[bold red]No process found using port {port}[/]")
        
        # Check if the port is open directly
        from wtfport.platform_utils import is_port_active
        if is_port_active(port):
            console.print(f"[yellow]However, port {port} is active.[/]")
            console.print("This may be due to insufficient permissions or the process is running in a container.")
            console.print("\nTry running with elevated privileges (sudo/administrator).")
        return

    console.print(f"[bold green]Port {port} is being used by:[/]")
    
    panel_content = Text()
    panel_content.append("\n[bold green]✓[/] ", style="")
    panel_content.append("Process:   ", style="bold")
    panel_content.append(f"{process_info['name']}\n", style="")
    
    panel_content.append("    PID:       ", style="bold")
    panel_content.append(f"{process_info['pid']}\n", style="")
    
    panel_content.append("    Command:   ", style="bold")
    panel_content.append(f"{process_info['command']}\n", style="")
    
    panel_content.append("    User:      ", style="bold")
    panel_content.append(f"{process_info['user']}\n", style="")
    
    panel_content.append("    Started:   ", style="bold")
    panel_content.append(f"{process_info['started']}\n", style="")
    
    console.print(Panel(panel_content, expand=False, padding=(1, 2)))

    console.print("[bold]Options:[/]")
    options_text = Text()
    
    if is_web:
        options_text.append("[O] Open in browser      ", style="bold cyan")
        options_text.append(f"(http://localhost:{port})\n", style="")
    
    options_text.append("[K] Kill process         ", style="bold red")
    options_text.append("(sudo may be required)\n", style="")
    
    options_text.append("[C] Copy command         ", style="bold yellow")
    options_text.append("(to clipboard)\n", style="")
    
    if log_file:
        options_text.append("[L] Tail log             ", style="bold green")
        options_text.append(f"({log_file})\n", style="")
    
    options_text.append("[Q] Quit", style="bold")
    
    console.print(options_text)

def print_all_ports(ports_info: List[Dict[str, Any]]):
    """Print a table of all listening ports."""
    if not ports_info:
        console.print("[bold yellow]No listening ports found[/]")
        console.print("This might be due to insufficient permissions.")
        console.print("Try running with elevated privileges (sudo/administrator).")
        return

    table = Table(title="Listening Ports", box=box.ROUNDED)
    
    table.add_column("Port", style="cyan", justify="right")
    table.add_column("Process", style="green")
    table.add_column("PID", style="blue", justify="right")
    table.add_column("User", style="yellow")
    table.add_column("Started", style="magenta")
    
    for info in sorted(ports_info, key=lambda x: x['port']):
        table.add_row(
            str(info['port']),
            info['process'],
            str(info['pid']),
            info['user'],
            info['started']
        )
    
    console.print(table)
    console.print("\nTip: run [bold]`wtfport <port>`[/] to inspect in detail.")

def print_watch_update(port: int, process_info: Optional[Dict[str, Any]], previous_info: Optional[Dict[str, Any]]):
    """Print updates for watch mode."""
    if not previous_info and process_info:
        console.print(f"[bold green]Process started:[/] {process_info['name']} (PID: {process_info['pid']})")
    elif previous_info and not process_info:
        console.print(f"[bold red]Process ended:[/] {previous_info['name']} (PID: {previous_info['pid']})")
    elif previous_info and process_info and previous_info['pid'] != process_info['pid']:
        console.print(f"[bold yellow]Process changed:[/] {previous_info['name']} (PID: {previous_info['pid']}) → {process_info['name']} (PID: {process_info['pid']})")

def print_kill_confirmation(port: int, process_info: Dict[str, Any], success: bool):
    """Print result of kill operation."""
    if success:
        console.print(f"[bold green]→ Process killed.[/] (PID: {process_info['pid']})")
    else:
        console.print(f"[bold red]→ Failed to kill process.[/] (PID: {process_info['pid']})")
        console.print("You might need to run with sudo or elevated privileges.")

def print_notification(port: int, process_info: Dict[str, Any]):
    """Print notification when a port becomes active."""
    console.print(f"[bold green]✓ Port {port} is now active![/]")
    console.print(f"Process: {process_info['name']} (PID: {process_info.get('pid', 'unknown')})")
    console.print(f"Command: {process_info['command']}")

def print_stats_summary(stats_summary: Dict[str, Any]):
    """Print a summary of port usage statistics."""
    console.print("\n[bold]Port Usage Statistics:[/]")
    
    console.print(f"\nTracking data for [bold cyan]{stats_summary['total_ports_tracked']}[/] ports and [bold cyan]{stats_summary['total_processes_tracked']}[/] processes.")
    console.print(f"Last updated: {stats_summary['last_updated']}")
    
    if stats_summary['top_ports']:
        console.print("\n[bold]Top Ports:[/]")
        table = Table(box=box.ROUNDED)
        table.add_column("Port", style="cyan", justify="right")
        table.add_column("Access Count", style="green", justify="right")
        table.add_column("Processes", style="yellow")
        table.add_column("Last Seen", style="magenta")
        
        for port_info in stats_summary['top_ports']:
            processes = ", ".join(port_info["processes"][:3])
            if len(port_info["processes"]) > 3:
                processes += f" +{len(port_info['processes']) - 3} more"
                
            table.add_row(
                str(port_info["port"]),
                str(port_info["count"]),
                processes,
                port_info["last_seen"].split("T")[0]  # Just show the date part
            )
        
        console.print(table)
    
    if stats_summary['top_processes']:
        console.print("\n[bold]Top Processes:[/]")
        table = Table(box=box.ROUNDED)
        table.add_column("Process", style="green")
        table.add_column("Access Count", style="cyan", justify="right")
        table.add_column("Used Ports", style="yellow")
        
        for proc_info in stats_summary['top_processes']:
            ports = ", ".join([str(p) for p in proc_info["ports"][:5]])
            if len(proc_info["ports"]) > 5:
                ports += f" +{len(proc_info['ports']) - 5} more"
                
            table.add_row(
                proc_info["name"],
                str(proc_info["count"]),
                ports
            )
        
        console.print(table)
    
    console.print("\nTip: Use [bold]`wtfport --stats-detail <port>`[/] to see detailed history for a specific port.")

def print_port_history(port_history: Dict[str, Any]):
    """Print detailed history for a specific port."""
    port = port_history["port"]
    
    console.print(f"\n[bold]History for Port {port}:[/]")
    console.print(f"First seen: {port_history['first_seen']}")
    console.print(f"Last seen: {port_history['last_seen']}")
    console.print(f"Times accessed: {port_history['count']}")
    
    if port_history["processes"]:
        console.print("\n[bold]Processes that have used this port:[/]")
        for process in port_history["processes"]:
            console.print(f"  • {process}")
            
def print_error(message: str):
    """Print an error message."""
    console.print(f"[bold red]Error: {message}[/]")

def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[bold yellow]Warning: {message}[/]")

def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]{message}[/]")

def print_info(message: str):
    """Print an informational message."""
    console.print(message)

def show_spinner(message: str):
    """Show a spinner with a message and return the progress object."""
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    )
    task = progress.add_task(description=message, total=None)
    progress.start()
    return progress, task