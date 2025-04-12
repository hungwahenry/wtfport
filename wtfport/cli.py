# wtfport/cli.py
"""
Command-line interface for wtfport.
"""
import time
import typer
from rich.prompt import Confirm
from typing import Optional, List
import sys
import os
import signal
import platform
import subprocess
import threading
import webbrowser
from typing_extensions import Annotated
from rich.markdown import Markdown

# Import local modules
from wtfport import output, core, log_tail, platform_utils, notifier
from wtfport.stats import PortStats

# Create Typer app with improved help
app = typer.Typer(
    name="wtfport",
    help="A terminal tool to identify, inspect, and interact with processes bound to specific ports.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

def handle_sigint(signum, frame):
    """Handle Ctrl+C gracefully."""
    output.console.print("\n\nExiting wtfport...")
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, handle_sigint)

def print_version(value: bool):
    """Print version and exit."""
    if value:
        from wtfport import __version__
        output.console.print(f"wtfport version: {__version__}")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    port: Annotated[
        Optional[int], 
        typer.Argument(
            help="Port number to check (e.g., 3000). If not specified, shows all listening ports."
        )
    ] = None,
    all: Annotated[
        bool, 
        typer.Option(
            "--all", "-a", 
            help="Show all listening ports and their associated processes."
        )
    ] = False,
    kill: Annotated[
        bool, 
        typer.Option(
            "--kill", "-k", 
            help="Kill the process using the specified port."
        )
    ] = False,
    json: Annotated[
        bool, 
        typer.Option(
            "--json", "-j", 
            help="Output results in JSON format for scripting."
        )
    ] = False,
    copy: Annotated[
        bool, 
        typer.Option(
            "--copy", "-c", 
            help="Copy the command of the process to clipboard."
        )
    ] = False,
    open: Annotated[
        bool, 
        typer.Option(
            "--open", "-o", 
            help="Open the specified port in a web browser (http://localhost:<port>)."
        )
    ] = False,
    watch: Annotated[
        bool, 
        typer.Option(
            "--watch", "-w", 
            help="Watch the specified port for changes."
        )
    ] = False,
    notify: Annotated[
        Optional[int], 
        typer.Option(
            help="Monitor and send a notification when the specified port becomes active."
        )
    ] = None,
    stats: Annotated[
        bool, 
        typer.Option(
            "--stats", "-s", 
            help="Show statistics of your most-used ports."
        )
    ] = False,
    stats_detail: Annotated[
        Optional[int], 
        typer.Option(
            "--stats-detail", 
            help="Show detailed statistics for a specific port."
        )
    ] = None,
    debug: Annotated[
        bool, 
        typer.Option(
            "--debug", "-d", 
            help="Show detailed debug information about your system."
        )
    ] = False,
    version: Annotated[
        bool, 
        typer.Option(
            "--version", "-v", 
            help="Show the version and exit.",
            callback=print_version,
        )
    ] = False,
    examples: Annotated[
        bool, 
        typer.Option(
            "--examples", "-e", 
            help="Show usage examples."
        )
    ] = False,
):
    """
    wtfport - A utility to quickly identify, inspect, and interact with processes bound to ports.
    
    [bold green]Examples:[/]
      wtfport 3000          Check what's using port 3000
      wtfport               Show all listening ports
      wtfport 8080 --kill   Kill the process on port 8080
      wtfport --notify 5000 Get notified when port 5000 becomes active
      wtfport --stats       Show port usage statistics
    """
    # Initialize port statistics
    port_stats = PortStats()
    
    # Show examples if requested
    if examples:
        examples_md = """
        # wtfport Usage Examples
        
        ## Basic Commands
        
        Check what's using port 3000:
        ```
        wtfport 3000
        ```
        
        List all listening ports:
        ```
        wtfport
        ```
        
        ## Process Management
        
        Kill a process on port 3000:
        ```
        wtfport 3000 --kill
        ```
        
        ## Monitoring
        
        Watch a port for changes:
        ```
        wtfport 3000 --watch
        ```
        
        Get notified when a port becomes active:
        ```
        wtfport --notify 5000
        ```
        
        ## Web Development
        
        Open a web server in browser:
        ```
        wtfport 3000 --open
        ```
        
        ## Statistics and History
        
        View port usage statistics:
        ```
        wtfport --stats
        ```
        
        View detailed history for a specific port:
        ```
        wtfport --stats-detail 3000
        ```
        
        ## Automation & Scripting
        
        Get JSON output for scripting:
        ```
        wtfport 3000 --json
        ```
        
        Copy the command to clipboard:
        ```
        wtfport 3000 --copy
        ```
        """
        output.console.print(Markdown(examples_md))
        return
    
    # Handle stats_detail option
    if stats_detail:
        port_history = port_stats.get_port_history(stats_detail)
        if port_history:
            output.print_port_history(port_history)
        else:
            output.print_warning(f"No statistics recorded for port {stats_detail}")
        return
        
    # Handle stats option
    if stats:
        stats_summary = port_stats.get_stats_summary()
        output.print_stats_summary(stats_summary)
        return

    # Handle debug information
    if debug:
        output.console.print("[bold]Debug Information:[/]")
        output.console.print(f"Python version: {sys.version}")
        output.console.print(f"Platform: {platform_utils.get_platform_info()}")
        output.console.print(f"Current user: {platform_utils.get_current_user()}")
        output.console.print(f"Elevated privileges: {platform_utils.has_admin_rights()}")
        return
    
    # Handle --notify option
    if notify:
        try:
            def on_port_active(process_info):
                output.print_notification(notify, process_info)
                title = f"Port {notify} is now active"
                message = f"{process_info['name']} (PID: {process_info.get('pid', 'unknown')})"
                notifier.send_desktop_notification(title, message)
                # Record this port access
                port_stats.record_port_access(notify, process_info)
            
            notifier.watch_for_port(notify, on_port_active)
        except KeyboardInterrupt:
            output.console.print("\nStopped watching.")
        except Exception as e:
            output.print_error(f"Error while watching port: {str(e)}")
        return
    
    # Handle --all option
    if all:
        try:
            ports_info = core.get_all_listening_ports()
            if json:
                print(core.to_json(ports_info))
            else:
                output.print_all_ports(ports_info)
                
            # Record each port access for statistics
            for port_info in ports_info:
                port_stats.record_port_access(port_info['port'], port_info)
        except Exception as e:
            output.print_error(f"Error getting port information: {str(e)}")
            if not platform_utils.has_admin_rights():
                output.console.print("\nTry running with elevated privileges (sudo/administrator).")
        return
    
    # If no port specified, show all ports as a default action
    if port is None:
        try:
            ports_info = core.get_all_listening_ports()
            if json:
                print(core.to_json(ports_info))
            else:
                output.print_all_ports(ports_info)
                
            # Record each port access for statistics
            for port_info in ports_info:
                port_stats.record_port_access(port_info['port'], port_info)
        except Exception as e:
            output.print_error(f"Error getting port information: {str(e)}")
            if not platform_utils.has_admin_rights():
                output.console.print("\nTry running with elevated privileges (sudo/administrator).")
        return
    
    # Get process info for the specified port
    try:
        process_info = core.get_process_by_port(port)
        
        # Record this port access for statistics
        port_stats.record_port_access(port, process_info)
        
        # Check if we can connect to the port even if no process is found
        if not process_info and core.check_port_connectivity(port):
            output.print_warning(f"Port {port} is active, but no process information is available.")
            output.console.print("This may be due to insufficient permissions or the process is running in a container.")
            
            if not json and not kill and not copy and not open and not watch:
                if not platform_utils.has_admin_rights():
                    output.console.print("\nTry running with elevated privileges (sudo/administrator).")
                
                # Create a placeholder process info
                process_info = {
                    'pid': 0,
                    'name': 'unknown',
                    'command': f'Process using port {port}',
                    'user': 'unknown',
                    'started': 'unknown',
                    'create_time': time.time()
                }
    except Exception as e:
        output.print_error(f"Error checking port {port}: {str(e)}")
        return
    
    # Handle JSON output
    if json:
        result = {"port": port}
        if process_info:
            result["process"] = process_info
        print(core.to_json(result))
        return
    
    # Handle kill option
    if kill:
        if process_info and process_info.get('pid', 0) > 0:
            output.console.print(f"Process on port {port}:")
            output.console.print(f"  {process_info['name']} (PID: {process_info['pid']})")
            
            if Confirm.ask("Are you sure you want to kill it?", default=False):
                success = core.kill_process(process_info['pid'])
                output.print_kill_confirmation(port, process_info, success)
                if not success and not platform_utils.has_admin_rights():
                    output.console.print("\nTry running with elevated privileges (sudo/administrator).")
        else:
            output.print_warning(f"No killable process found on port {port}")
            # Try force-killing the port if we can detect it's active
            if core.check_port_connectivity(port):
                if Confirm.ask("Try force-killing whatever is using this port?", default=False):
                    success = core.force_kill_port(port)
                    if success:
                        output.print_success(f"Successfully freed port {port}")
                    else:
                        output.print_error(f"Failed to free port {port}")
                        if not platform_utils.has_admin_rights():
                            output.console.print("\nTry running with elevated privileges (sudo/administrator).")
        return
    
    # Handle copy option
    if copy and process_info:
        command = process_info.get('command', '')
        if command and command != f'Process using port {port}':
            success = platform_utils.copy_to_clipboard(command)
            if success:
                output.print_success("Command copied to clipboard!")
            else:
                output.print_error("Failed to copy to clipboard.")
        else:
            output.print_warning("No command available to copy.")
        return
    
    # Handle open option
    if open:
        is_web = core.is_web_server(port) or core.check_port_connectivity(port)
        if is_web:
            try:
                webbrowser.open(f"http://localhost:{port}")
                output.print_success(f"Opened http://localhost:{port} in browser")
            except Exception:
                output.print_error("Failed to open browser")
        else:
            output.print_warning(f"No active server detected on port {port}.")
        return
    
    # Handle watch option
    if watch:
        output.console.print(f"Watching port {port}...")
        output.console.print("Press Ctrl+C to stop watching.\n")
        
        previous_info = process_info
        if process_info:
            output.console.print(f"Process: {process_info['name']} (PID: {process_info.get('pid', 'unknown')})")
        
        try:
            while True:
                time.sleep(1)
                current_info = core.get_process_by_port(port)
                
                # Also check direct port connectivity
                if not current_info and core.check_port_connectivity(port):
                    current_info = {
                        'pid': 0,
                        'name': 'unknown',
                        'command': f'Process using port {port}',
                        'user': 'unknown',
                        'started': 'just detected',
                        'create_time': time.time()
                    }
                
                if current_info != previous_info:
                    output.print_watch_update(port, current_info, previous_info)
                    # Record any changes in statistics
                    if current_info:
                        port_stats.record_port_access(port, current_info)
                    previous_info = current_info
        except KeyboardInterrupt:
            output.console.print("\nStopped watching.")
        return
    
    # Default: show process details and interactive options
    is_web = (process_info and core.is_web_server(port)) or core.check_port_connectivity(port)
    log_file = process_info and core.detect_log_file(process_info)
    
    output.print_process_detail(port, process_info, is_web, log_file)
    
    if process_info:
        while True:
            try:
                choice = input("\nEnter option (O/K/C/L/Q): ").upper()
                
                if choice == 'Q':
                    break
                elif choice == 'O' and is_web:
                    try:
                        webbrowser.open(f"http://localhost:{port}")
                        output.print_success(f"Opened http://localhost:{port} in browser")
                    except Exception:
                        output.print_error("Failed to open browser")
                elif choice == 'K':
                    if process_info.get('pid', 0) > 0:
                        if Confirm.ask("Are you sure you want to kill this process?", default=False):
                            success = core.kill_process(process_info['pid'])
                            output.print_kill_confirmation(port, process_info, success)
                            if success:
                                break
                            elif not platform_utils.has_admin_rights():
                                output.console.print("\nTry running with elevated privileges (sudo/administrator).")
                    else:
                        output.print_warning("Cannot kill this process - no PID available.")
                        if core.check_port_connectivity(port):
                            if Confirm.ask("Try force-killing whatever is using this port?", default=False):
                                success = core.force_kill_port(port)
                                if success:
                                    output.print_success(f"Successfully freed port {port}")
                                    break
                                else:
                                    output.print_error(f"Failed to free port {port}")
                elif choice == 'C':
                    command = process_info.get('command', '')
                    if command and command != f'Process using port {port}':
                        success = platform_utils.copy_to_clipboard(command)
                        if success:
                            output.print_success("Command copied to clipboard!")
                        else:
                            output.print_error("Failed to copy to clipboard.")
                    else:
                        output.print_warning("No command available to copy.")
                elif choice == 'L' and log_file:
                    try:
                        log_tail.tail_log_in_console(log_file)
                    except KeyboardInterrupt:
                        output.console.print("\n[yellow]Stopped tailing log.[/]")
                    except Exception as e:
                        output.print_error(f"Error tailing log: {str(e)}")
                else:
                    output.print_warning("Invalid option")
            except KeyboardInterrupt:
                break
            except Exception as e:
                output.print_error(f"Error: {str(e)}")
                break

if __name__ == "__main__":
    app()