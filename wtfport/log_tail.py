# wtfport/log_tail.py
"""
Log handling utilities for wtfport.
"""
import os
import time
from typing import Optional, TextIO, List

from wtfport.output import console, print_error, print_warning, print_info

def tail_log_in_console(log_path: str, lines: int = 10, follow: bool = True):
    """
    Tail a log file directly in the console.
    
    Args:
        log_path: Path to the log file
        lines: Number of lines to show initially
        follow: Whether to continue watching the file
    """
    if not os.path.exists(log_path):
        print_error(f"Log file not found: {log_path}")
        return
    
    file_size = os.path.getsize(log_path)
    if file_size == 0:
        print_warning(f"Log file is empty: {log_path}")
        if not follow:
            return
    
    # Show the last few lines first
    with open(log_path, 'r', errors='replace') as file:
        print_info(f"\n=== Tailing log: {log_path} ===\n")
        try:
            # Get last lines
            last_lines = get_last_lines(file, lines)
            for line in last_lines:
                console.print(line.rstrip())
        except UnicodeDecodeError:
            print_warning("Unable to display log content (binary file)")
            return
    
    if not follow:
        return
        
    # Continue to follow the file
    print_info("\n(Press Ctrl+C to stop watching the log)\n")
    try:
        follow_file(log_path)
    except KeyboardInterrupt:
        print_info("\nStopped watching log.")
    except Exception as e:
        print_error(f"Error while tailing log: {str(e)}")

def get_last_lines(file: TextIO, n: int) -> List[str]:
    """Get the last n lines from a file."""
    try:
        # Quick implementation for small files
        lines = file.readlines()
        return lines[-n:] if len(lines) > n else lines
    except Exception:
        # More memory-efficient implementation for large files
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            
            # If file is empty, return empty list
            if file_size == 0:
                return []
            
            # Start with a reasonable buffer size
            avg_line_length = 100
            buffer_size = avg_line_length * n
            if buffer_size > file_size:
                buffer_size = file_size
            
            # Read chunks from the end until we have enough lines
            lines = []
            chars_read = 0
            
            while len(lines) <= n and chars_read < file_size:
                # Move back from end or start of file
                chars_to_read = min(buffer_size, file_size - chars_read)
                file.seek(file_size - chars_read - chars_to_read)
                buffer = file.read(chars_to_read)
                
                # Count lines in the buffer
                lines = buffer.splitlines() + lines
                chars_read += chars_to_read
                
                # If we've hit the start of the file, we're done
                if file.tell() == 0:
                    break
            
            # Return only the last n lines
            return lines[-n:] if len(lines) > n else lines
        except Exception:
            # Fall back to simple implementation if something goes wrong
            file.seek(0)
            lines = file.readlines()
            return lines[-n:] if len(lines) > n else lines

def follow_file(log_path: str):
    """Follow a file as it grows, similar to 'tail -f'."""
    with open(log_path, 'r', errors='replace') as file:
        # Move to the end of the file
        file.seek(0, os.SEEK_END)
        
        while True:
            line = file.readline()
            if line:
                console.print(line.rstrip())
            else:
                # Check if file has been truncated or rotated
                current_position = file.tell()
                file_size = os.path.getsize(log_path)
                
                if file_size < current_position:
                    # File was truncated, start from beginning
                    print_warning("Log file was truncated, restarting...")
                    file.seek(0)
                else:
                    # Just wait for more content
                    time.sleep(0.1)

def detect_common_log_locations(process_name: str) -> List[str]:
    """Detect common log locations for a given process."""
    common_locations = [
        f"/var/log/{process_name}/{process_name}.log",
        f"/var/log/{process_name}.log",
        f"/var/log/syslog",
        f"/var/log/system.log",
        f"~/.local/share/{process_name}/logs/latest.log",
        f"~/.{process_name}/logs/latest.log",
        f"./logs/{process_name}.log",
        f"./{process_name}.log"
    ]
    
    valid_locations = []
    for location in common_locations:
        expanded = os.path.expanduser(location)
        if os.path.exists(expanded) and os.path.isfile(expanded):
            valid_locations.append(expanded)
            
    return valid_locations

def extract_log_path_from_command(command: str) -> Optional[str]:
    """
    Extract a log file path from a command string.
    
    Looks for common patterns like --log=file.log, > file.log, etc.
    """
    log_indicators = [
        ("--log=", " "),
        ("--logfile=", " "),
        ("-l ", " "),
        ("log=", " "),
        ("> ", " "),
        (">> ", " "),
        ("2> ", " "),
        ("2>> ", " ")
    ]
    
    command = command.lower()
    
    for prefix, suffix in log_indicators:
        if prefix in command:
            parts = command.split(prefix, 1)
            if len(parts) > 1:
                # Extract until next space or end of string
                if suffix == " " and " " in parts[1]:
                    log_path = parts[1].split(" ", 1)[0].strip()
                else:
                    log_path = parts[1].split(suffix, 1)[0].strip()
                
                # Expand user directory if needed
                log_path = os.path.expanduser(log_path)
                
                if os.path.exists(log_path) and os.path.isfile(log_path):
                    return log_path
    
    return None