"""
Statistics tracking for wtfport.
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Define the stats file location
STATS_DIR = Path.home() / ".wtfport"
STATS_FILE = STATS_DIR / "stats.json"

class PortStats:
    """Track port usage statistics."""
    
    def __init__(self):
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Any]:
        """Load statistics from disk."""
        if not STATS_DIR.exists():
            STATS_DIR.mkdir(exist_ok=True)
        
        if not STATS_FILE.exists():
            # Initialize with empty stats
            return {
                "version": 1,
                "ports": {},
                "processes": {},
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupt or cannot be read, start fresh
            return {
                "version": 1,
                "ports": {},
                "processes": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_stats(self):
        """Save statistics to disk."""
        self.stats["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(STATS_FILE, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write the stats
    
    def record_port_access(self, port: int, process_info: Optional[Dict[str, Any]] = None):
        """Record that a port was accessed."""
        port_str = str(port)
        timestamp = datetime.now().isoformat()
        
        # Update port statistics
        if port_str not in self.stats["ports"]:
            self.stats["ports"][port_str] = {
                "count": 0,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "processes": []
            }
        
        port_stats = self.stats["ports"][port_str]
        port_stats["count"] += 1
        port_stats["last_seen"] = timestamp
        
        # Update process information if provided
        if process_info:
            process_name = process_info.get("name", "unknown")
            
            # Add to processes used with this port
            if process_name not in port_stats["processes"]:
                port_stats["processes"].append(process_name)
            
            # Update global process statistics
            if process_name not in self.stats["processes"]:
                self.stats["processes"][process_name] = {
                    "count": 0,
                    "ports": [],
                    "first_seen": timestamp,
                    "last_seen": timestamp
                }
            
            proc_stats = self.stats["processes"][process_name]
            proc_stats["count"] += 1
            proc_stats["last_seen"] = timestamp
            
            if port_str not in proc_stats["ports"]:
                proc_stats["ports"].append(port_str)
        
        self._save_stats()
    
    def get_top_ports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently accessed ports."""
        ports = []
        
        for port, data in self.stats["ports"].items():
            ports.append({
                "port": int(port),
                "count": data["count"],
                "last_seen": data["last_seen"],
                "processes": data["processes"]
            })
        
        # Sort by count (most frequent first)
        ports.sort(key=lambda x: x["count"], reverse=True)
        
        return ports[:limit]
    
    def get_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently seen processes."""
        processes = []
        
        for proc, data in self.stats["processes"].items():
            processes.append({
                "name": proc,
                "count": data["count"],
                "ports": [int(p) for p in data["ports"]],
                "last_seen": data["last_seen"]
            })
        
        # Sort by count (most frequent first)
        processes.sort(key=lambda x: x["count"], reverse=True)
        
        return processes[:limit]
    
    def get_port_history(self, port: int) -> Optional[Dict[str, Any]]:
        """Get the history for a specific port."""
        port_str = str(port)
        
        if port_str in self.stats["ports"]:
            data = self.stats["ports"][port_str]
            return {
                "port": port,
                "count": data["count"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"],
                "processes": data["processes"]
            }
        
        return None
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get a summary of all statistics."""
        return {
            "total_ports_tracked": len(self.stats["ports"]),
            "total_processes_tracked": len(self.stats["processes"]),
            "top_ports": self.get_top_ports(5),
            "top_processes": self.get_top_processes(5),
            "last_updated": self.stats["last_updated"]
        }