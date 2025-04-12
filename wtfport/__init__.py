"""
wtfport - A terminal tool to identify, inspect, and interact with processes bound to specific ports.
"""

__version__ = "0.1.0"

# Direct imports to avoid circular dependencies
from wtfport.core import get_process_by_port, get_all_listening_ports, kill_process