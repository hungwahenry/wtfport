# wtfport/core.py
"""
Core functionality for wtfport.
"""
import os
import psutil
import socket
import platform
import subprocess
from datetime import datetime
import json
import re
import time
from typing import Dict, List, Optional, Any

def get_process_by_port(port: int) -> Optional[Dict[str, Any]]:
    """Get process information for a specific port using multiple methods."""
    # Try using psutil first (cross-platform but may have permission issues)
    process_info = _get_process_by_port_psutil(port)
    if process_info:
        return process_info
    
    # Fall back to platform-specific commands
    system = platform.system()
    if system == "Darwin":
        return _get_process_by_port_lsof(port)
    elif system == "Linux":
        return _get_process_by_port_ss(port) or _get_process_by_port_lsof(port)
    elif system == "Windows":
        return _get_process_by_port_netstat(port)
    
    return None

def _get_process_by_port_psutil(port: int) -> Optional[Dict[str, Any]]:
    """Get process info using psutil (cross-platform but may need elevated privileges)."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                process = psutil.Process(conn.pid)
                return {
                    'pid': process.pid,
                    'name': process.name(),
                    'command': ' '.join(process.cmdline()),
                    'user': process.username(),
                    'started': get_readable_time(process.create_time()),
                    'create_time': process.create_time()
                }
    except (psutil.AccessDenied, psutil.NoSuchProcess, PermissionError):
        return None
    return None

def _get_process_by_port_lsof(port: int) -> Optional[Dict[str, Any]]:
    """Get process info using lsof (macOS/Linux)."""
    try:
        output = subprocess.check_output(
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-n", "-P"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            if len(lines) > 1:  # Skip header
                parts = lines[1].split()
                if len(parts) >= 2:
                    process_name = parts[0]
                    pid = int(parts[1])
                    
                    # Get additional details
                    try:
                        process = psutil.Process(pid)
                        return {
                            'pid': pid,
                            'name': process_name,
                            'command': ' '.join(process.cmdline()),
                            'user': process.username(),
                            'started': get_readable_time(process.create_time()),
                            'create_time': process.create_time()
                        }
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        # Basic info if we can't get details
                        return {
                            'pid': pid,
                            'name': process_name,
                            'command': f"{process_name} (details unavailable)",
                            'user': "unknown",
                            'started': "unknown",
                            'create_time': time.time()
                        }
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None

def _get_process_by_port_ss(port: int) -> Optional[Dict[str, Any]]:
    """Get process info using ss (Linux)."""
    try:
        output = subprocess.check_output(
            ["ss", "-lptn", f"sport = :{port}"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            if len(lines) > 1:  # Skip header
                for line in lines[1:]:
                    if f":{port}" in line and "LISTEN" in line:
                        # Parse the pid
                        pid_match = re.search(r'pid=(\d+)', line)
                        if pid_match:
                            pid = int(pid_match.group(1))
                            try:
                                process = psutil.Process(pid)
                                return {
                                    'pid': pid,
                                    'name': process.name(),
                                    'command': ' '.join(process.cmdline()),
                                    'user': process.username(),
                                    'started': get_readable_time(process.create_time()),
                                    'create_time': process.create_time()
                                }
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                # Basic info if we can't get details
                                return {
                                    'pid': pid,
                                    'name': f"process-{pid}",
                                    'command': f"Details unavailable (pid: {pid})",
                                    'user': "unknown",
                                    'started': "unknown",
                                    'create_time': time.time()
                                }
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None

def _get_process_by_port_netstat(port: int) -> Optional[Dict[str, Any]]:
    """Get process info using netstat (Windows)."""
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "TCP"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = int(parts[-1])
                        try:
                            process = psutil.Process(pid)
                            return {
                                'pid': pid,
                                'name': process.name(),
                                'command': ' '.join(process.cmdline()),
                                'user': process.username(),
                                'started': get_readable_time(process.create_time()),
                                'create_time': process.create_time()
                            }
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            # Basic info if we can't get details
                            return {
                                'pid': pid,
                                'name': f"process-{pid}",
                                'command': f"Details unavailable (pid: {pid})",
                                'user': "unknown",
                                'started': "unknown",
                                'create_time': time.time()
                            }
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None

def get_all_listening_ports() -> List[Dict[str, Any]]:
    """Get all listening ports and their associated processes."""
    result = []
    
    # First try using psutil
    try:
        psutil_result = _get_all_ports_psutil()
        if psutil_result:
            result.extend(psutil_result)
    except Exception:
        pass
    
    # Then try platform-specific methods if psutil didn't return anything
    if not result:
        system = platform.system()
        if system == "Darwin":  # macOS
            result = _get_all_ports_lsof()
        elif system == "Linux":
            result = _get_all_ports_ss() or _get_all_ports_lsof()
        elif system == "Windows":
            result = _get_all_ports_netstat()
    
    # Remove duplicates based on port
    unique_results = {}
    for item in result:
        port = item['port']
        if port not in unique_results:
            unique_results[port] = item
    
    return list(unique_results.values())

def _get_all_ports_psutil() -> List[Dict[str, Any]]:
    """Get all listening ports using psutil."""
    result = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    result.append({
                        'port': conn.laddr.port,
                        'pid': conn.pid,
                        'process': process.name(),
                        'command': ' '.join(process.cmdline()),
                        'user': process.username(),
                        'started': get_readable_time(process.create_time()),
                        'create_time': process.create_time()
                    })
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
    except psutil.AccessDenied:
        pass
    return result

def _get_all_ports_lsof() -> List[Dict[str, Any]]:
    """Get all listening ports using lsof (macOS/Linux)."""
    result = []
    try:
        output = subprocess.check_output(
            ["lsof", "-i", "-sTCP:LISTEN", "-n", "-P"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 9:
                    process_name = parts[0]
                    pid = int(parts[1])
                    # Parse port from address
                    addr_part = parts[8]
                    port_match = re.search(r':(\d+)$', addr_part)
                    if port_match:
                        port = int(port_match.group(1))
                        try:
                            process = psutil.Process(pid)
                            result.append({
                                'port': port,
                                'pid': pid,
                                'process': process_name,
                                'command': ' '.join(process.cmdline()),
                                'user': process.username(),
                                'started': get_readable_time(process.create_time()),
                                'create_time': process.create_time()
                            })
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            result.append({
                                'port': port,
                                'pid': pid,
                                'process': process_name,
                                'command': f"{process_name} (details unavailable)",
                                'user': "unknown",
                                'started': "unknown",
                                'create_time': time.time()
                            })
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return result

def _get_all_ports_ss() -> List[Dict[str, Any]]:
    """Get all listening ports using ss (Linux)."""
    result = []
    try:
        output = subprocess.check_output(
            ["ss", "-lptn"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if "LISTEN" in line:
                    # Parse port
                    port_match = re.search(r':(\d+)\s', line)
                    # Parse pid
                    pid_match = re.search(r'pid=(\d+)', line)
                    if port_match and pid_match:
                        port = int(port_match.group(1))
                        pid = int(pid_match.group(1))
                        try:
                            process = psutil.Process(pid)
                            result.append({
                                'port': port,
                                'pid': pid,
                                'process': process.name(),
                                'command': ' '.join(process.cmdline()),
                                'user': process.username(),
                                'started': get_readable_time(process.create_time()),
                                'create_time': process.create_time()
                            })
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            result.append({
                                'port': port,
                                'pid': pid,
                                'process': f"process-{pid}",
                                'command': f"Details unavailable (pid: {pid})",
                                'user': "unknown",
                                'started': "unknown",
                                'create_time': time.time()
                            })
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return result

def _get_all_ports_netstat() -> List[Dict[str, Any]]:
    """Get all listening ports using netstat (Windows)."""
    result = []
    try:
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "TCP"], 
            text=True
        )
        if output:
            lines = output.strip().split('\n')
            for line in lines:
                if "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        # Parse port from address
                        addr_part = parts[1]
                        port_match = re.search(r':(\d+)$', addr_part)
                        if port_match:
                            port = int(port_match.group(1))
                            pid = int(parts[-1])
                            try:
                                process = psutil.Process(pid)
                                result.append({
                                    'port': port,
                                    'pid': pid,
                                    'process': process.name(),
                                    'command': ' '.join(process.cmdline()),
                                    'user': process.username(),
                                    'started': get_readable_time(process.create_time()),
                                    'create_time': process.create_time()
                                })
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                result.append({
                                    'port': port,
                                    'pid': pid,
                                    'process': f"process-{pid}",
                                    'command': f"Details unavailable (pid: {pid})",
                                    'user': "unknown",
                                    'started': "unknown",
                                    'create_time': time.time()
                                })
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return result

def kill_process(pid: int) -> bool:
    """Kill a process by PID."""
    try:
        process = psutil.Process(pid)
        process.terminate()
        # Give it some time to terminate
        try:
            process.wait(timeout=3)
        except psutil.TimeoutExpired:
            # If it doesn't terminate gracefully, force kill it
            process.kill()
            process.wait(timeout=1)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
        # Try platform-specific force kill if psutil fails
        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
            else:
                subprocess.run(["kill", "-9", str(pid)], check=True)
            return True
        except Exception:
            return False

def get_readable_time(timestamp: float) -> str:
    """Convert a timestamp to a human-readable string like '3m ago'."""
    now = datetime.now().timestamp()
    diff = now - timestamp
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes}m ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff / 86400)
        return f"{days}d ago"

def is_web_server(port: int) -> bool:
    """Determine if a port is likely running a web server."""
    common_web_ports = [80, 443, 3000, 4000, 5000, 8000, 8080, 8888]
    if port in common_web_ports:
        return True
    
    # Try to check if it responds to HTTP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(('localhost', port))
            s.send(b'GET / HTTP/1.0\r\n\r\n')
            response = s.recv(1024)
            return response.startswith(b'HTTP/')
    except (socket.timeout, ConnectionRefusedError, OSError):
        pass
    
    return False

def to_json(data: Any) -> str:
    """Convert data to JSON string."""
    def clean_data(item):
        """Remove non-serializable items."""
        if isinstance(item, dict):
            return {k: clean_data(v) for k, v in item.items() if k != 'create_time'}
        elif isinstance(item, list):
            return [clean_data(i) for i in item]
        return item
    
    clean_result = clean_data(data)
    return json.dumps(clean_result, indent=2)

def detect_log_file(process_info: Dict[str, Any]) -> Optional[str]:
    """Try to detect a log file for the given process."""
    cmd = process_info.get('command', '').lower()
    log_indicators = ["--log=", "--logfile=", "-l ", "log=", ">", ">>"]
    
    for indicator in log_indicators:
        if indicator in cmd:
            parts = cmd.split(indicator, 1)
            if len(parts) > 1:
                log_path = parts[1].split()[0].strip()
                if os.path.exists(log_path):
                    return log_path
    
    # Check for common log locations based on process name
    process_name = process_info.get('name', '').lower()
    common_locations = [
        f"/var/log/{process_name}/{process_name}.log",
        f"/var/log/{process_name}.log",
        f"~/.local/share/{process_name}/log.txt"
    ]
    
    for location in common_locations:
        expanded = os.path.expanduser(location)
        if os.path.exists(expanded):
            return expanded
            
    return None

def check_port_connectivity(port: int, timeout: float = 1.0) -> bool:
    """Check if a port can be connected to."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception:
        return False

def force_kill_port(port: int) -> bool:
    """Force kill whatever is using the port."""
    system = platform.system()
    
    try:
        if system == "Darwin" or system == "Linux":  # macOS/Linux
            # Try using fuser to kill the process
            try:
                subprocess.run(["fuser", "-k", f"{port}/tcp"], check=True)
                time.sleep(0.5)  # Give it some time
                return not check_port_connectivity(port)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            
            # Try lsof
            try:
                output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True)
                if output:
                    pids = output.strip().split()
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-9", pid], check=True)
                        except Exception:
                            pass
                    time.sleep(0.5)  # Give it some time
                    return not check_port_connectivity(port)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        
        elif system == "Windows":
            try:
                # Find and kill the process using netstat
                output = subprocess.check_output(
                    ["netstat", "-ano", "-p", "TCP"], 
                    text=True
                )
                for line in output.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            subprocess.run(["taskkill", "/F", "/PID", pid], check=True)
                            time.sleep(0.5)  # Give it some time
                            return not check_port_connectivity(port)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
    except Exception:
        pass
    
    return False