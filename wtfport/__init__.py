"""
wtfport - A terminal tool to identify, inspect, and interact with processes bound to specific ports.
"""

from .version import __version__

from wtfport.core import get_process_by_port, get_all_listening_ports, kill_process
