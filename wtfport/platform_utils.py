# wtfport/platform_utils.py
"""
Platform-specific utilities for wtfport.
"""
import os
import platform
import subprocess
import webbrowser
import socket
import sys
import time  # Add this import
from typing import Optional, Dict, Any

def open_browser(port: int):
    """Open the default browser to localhost:port."""
    url = f"http://localhost:{port}"
    webbrowser.open(url)

def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return _platform_copy(text)

def _platform_copy(text: str) -> bool:
    """Fallback platform-specific clipboard utilities."""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif system == "Windows":
            subprocess.run(["clip"], input=text.encode(), check=True)
            return True
        elif system == "Linux":
            # Try xclip first, then xsel
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
                return True
            except FileNotFoundError:
                try:
                    subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    return False
    except subprocess.SubprocessError:
        return False
    return False

def tail_log(log_path: str):
    """Open a new terminal window and tail the log file."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        os.system(f"open -a Terminal 'tail -f {log_path}'")
    elif system == "Linux":
        # Try different terminal emulators
        terminals = ["gnome-terminal", "xterm", "konsole", "terminator"]
        for term in terminals:
            try:
                subprocess.run(["which", term], check=True, stdout=subprocess.PIPE)
                if term == "gnome-terminal":
                    subprocess.Popen([term, "--", "tail", "-f", log_path])
                else:
                    subprocess.Popen([term, "-e", f"tail -f {log_path}"])
                return
            except subprocess.SubprocessError:
                continue
    elif system == "Windows":
        subprocess.Popen(["powershell", "-Command", f"Get-Content -Path '{log_path}' -Wait"])

def is_port_active(port: int) -> bool:
    """Check if a port is active/open regardless of having process info."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except Exception:
        return False

def force_kill_port(port: int) -> bool:
    """Force kill whatever is using the port."""
    from wtfport.core import check_port_connectivity
    
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

def get_platform_info() -> str:
    """Get detailed platform information."""
    system = platform.system()
    version = platform.version()
    machine = platform.machine()
    
    if system == "Darwin":
        try:
            mac_version = subprocess.check_output(["sw_vers", "-productVersion"], text=True).strip()
            return f"macOS {mac_version} ({machine})"
        except Exception:
            return f"macOS {version} ({machine})"
    elif system == "Linux":
        try:
            # Try to get Linux distribution info
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                    for line in lines:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=")[1].strip().strip('"')
                            return f"{distro} ({machine})"
        except Exception:
            pass
        return f"Linux {version} ({machine})"
    else:
        return f"{system} {version} ({machine})"

def get_current_user() -> str:
    """Get the current user."""
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        return os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'

def has_admin_rights() -> bool:
    """Check if the script is running with administrative privileges."""
    system = platform.system()
    
    if system == "Windows":
        try:
            # Check if running as administrator on Windows
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        # On Unix-like systems, check if effective user ID is 0 (root)
        try:
            return os.geteuid() == 0
        except AttributeError:
            # fallback for systems that don't have geteuid
            try:
                return subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip() == "0"
            except Exception:
                return False

def send_platform_notification(title: str, message: str) -> bool:
    """Send a platform-specific notification."""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run([
                "osascript", 
                "-e", 
                f'display notification "{message}" with title "{title}"'
            ])
            return True
        elif system == "Linux":
            subprocess.run([
                "notify-send", 
                title, 
                message,
                "--icon=terminal"
            ])
            return True
        elif system == "Windows":
            # Use PowerShell to create a notification
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
            $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
            $text = $xml.GetElementsByTagName('text')
            $text[0].AppendChild($xml.CreateTextNode('{title}'))
            $text[1].AppendChild($xml.CreateTextNode('{message}'))

            $toast = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('wtfport')
            $toast.Show($xml)
            """
            subprocess.run(["powershell", "-Command", ps_script])
            return True
    except Exception:
        return False