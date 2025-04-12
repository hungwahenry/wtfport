# wtfport/notifier.py
"""
Notification system for wtfport.
"""
import time
import threading
from typing import Callable, Dict, Any

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

from wtfport.output import console, print_info
from wtfport.platform_utils import send_platform_notification
from wtfport.core import check_port_connectivity, get_process_by_port

def watch_for_port(port: int, callback: Callable[[Dict[str, Any]], None], check_interval: int = 1):
    """
    Watch for a port to become active and call the callback when it does.
    
    Args:
        port: The port number to watch
        callback: Function to call with the process info when port becomes active
        check_interval: How often to check for the port (in seconds)
    """
    console.print(f"Watching for port {port} to open...")
    console.print("Press Ctrl+C to stop watching.")
    
    # First, check if the port is already in use
    process_info = get_process_by_port(port)
    if process_info:
        callback(process_info)
        return
    
    try:
        while True:
            # Also check if we can connect to the port directly
            is_connectable = check_port_connectivity(port)
            
            # Then check for process
            process_info = get_process_by_port(port)
            
            if process_info or is_connectable:
                if process_info:
                    callback(process_info)
                else:
                    # Create a placeholder process info
                    dummy_info = {
                        'pid': 0,
                        'name': 'unknown',
                        'command': f'Process using port {port}',
                        'user': 'unknown',
                        'started': 'just now',
                        'create_time': time.time()
                    }
                    callback(dummy_info)
                    
                    # Continue trying to get real process info
                    console.print("Attempting to get process details...")
                    for _ in range(5):  # Try a few more times to get process details
                        time.sleep(1)
                        process_info = get_process_by_port(port)
                        if process_info:
                            callback(process_info)
                            break
                break
            time.sleep(check_interval)
    except KeyboardInterrupt:
        console.print("\nStopped watching.")

def send_desktop_notification(title: str, message: str, timeout: int = 10) -> bool:
    """Send a desktop notification."""
    if HAS_PLYER:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="wtfport",
                timeout=timeout
            )
            return True
        except Exception:
            pass
    
    # Fall back to platform-specific notification methods
    return send_platform_notification(title, message)

def start_notification_thread(port: int) -> threading.Thread:
    """Start a background thread to watch for a port."""
    from wtfport.output import print_notification
    
    def on_port_active(process_info):
        # Print to console
        print_notification(port, process_info)
        
        # Send desktop notification
        title = f"Port {port} is now active"
        message = f"{process_info['name']} (PID: {process_info.get('pid', 'unknown')})"
        send_desktop_notification(title, message)
    
    thread = threading.Thread(
        target=watch_for_port,
        args=(port, on_port_active),
        daemon=True
    )
    thread.start()
    return thread