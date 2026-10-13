"""
AuthSentinel Collector with SSH Monitoring
===========================================
Extends the standard collector to also monitor SSH authentication events
and forward them to the backend dashboard.

Combines Windows Security Events (Event ID 4624/4625) with SSH login monitoring.
"""

import argparse
import os
import sys
import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from colorama import Fore, Style, init as colorama_init

# Import SSH monitor module
try:
    from ssh_monitor import get_ssh_events, SSHEvent
except ImportError:
    print("[!] ssh_monitor.py not found in same directory")
    sys.exit(1)

colorama_init(autoreset=True, convert=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)

COLLECTOR_SECRET = os.environ.get("AS_COLLECTOR_SECRET", "authsentinel-lab-secret-2026")

class SSHEventForwarder:
    """Forwards SSH events to the AuthSentinel backend."""
    
    def __init__(self, backend_url: str, label: str, collector_secret: str = COLLECTOR_SECRET):
        self.backend_url = backend_url.rstrip("/")
        self.label = label
        self.collector_secret = collector_secret
        self._headers = {
            "Content-Type": "application/json",
            "X-Collector-Secret": self.collector_secret,
            "X-Source-Label": self.label,
        }
        self._running = True
        self._ssh_thread = threading.Thread(target=self._ssh_monitor_worker, daemon=True)
        self._ssh_thread.start()

    def _ssh_monitor_worker(self):
        """Background thread that monitors SSH events and forwards them."""
        print(f"{Fore.CYAN}[SSH Monitor] Starting SSH authentication listener...{Style.RESET_ALL}")
        
        try:
            for ssh_event in get_ssh_events():
                if not self._running:
                    break
                
                # Convert SSH event to backend format
                payload = self._format_ssh_event(ssh_event)
                self._send_event(payload)
                
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}[SSH Monitor] Stopped by user{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[SSH Monitor Error] {e}{Style.RESET_ALL}")

    def _format_ssh_event(self, ssh_event: SSHEvent) -> dict:
        """Convert SSHEvent to backend event format."""
        
        # Map SSH event types to backend alert types
        event_type_map = {
            "LOGIN-OK": "SUCCESSFUL_LOGIN",
            "LOGIN-FAIL": "FAILED_LOGIN",
            "INVALID-USER": "INVALID_USER_ATTEMPT",
            "BRUTE-FORCE": "BRUTE_FORCE_DETECTED",
        }
        
        alert_type = event_type_map.get(ssh_event.event_type, "SSH_SECURITY_EVENT")
        
        # Determine risk level
        risk_level_map = {
            "LOGIN-OK": "LOW",
            "LOGIN-FAIL": "MEDIUM",
            "INVALID-USER": "MEDIUM",
            "BRUTE-FORCE": "HIGH",
        }
        risk_level = risk_level_map.get(ssh_event.event_type, "MEDIUM")
        
        return {
            "event_id": 9999,  # Custom SSH event ID
            "timestamp": ssh_event.timestamp,
            "username": ssh_event.username,
            "source_ip": ssh_event.source_ip,
            "source_host": ssh_event.source_ip,  # Will be resolved by backend
            "target_computer": self.label,
            "logon_type": "RemoteInteractive",
            "logon_type_description": "SSH Remote Login",
            "status": "SUCCESS" if ssh_event.event_type == "LOGIN-OK" else "FAILURE",
            "alert_type": alert_type,
            "risk_level": risk_level,
            "reason": f"SSH {ssh_event.event_type}: {ssh_event.method or 'password'} authentication",
            "raw_record_id": None,
        }

    def _send_event(self, payload: dict) -> bool:
        """Send event to backend."""
        try:
            response = requests.post(
                f"{self.backend_url}/api/events",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
            
            if response.status_code == 200:
                print(f"{Fore.GREEN}[SSH Event Sent] {payload.get('alert_type')} - {payload.get('username')}@{payload.get('source_ip')}{Style.RESET_ALL}")
                return True
            elif response.status_code == 403:
                print(f"{Fore.RED}[SSH Error] Invalid collector secret{Style.RESET_ALL}")
                return False
            else:
                print(f"{Fore.RED}[SSH Error] HTTP {response.status_code}: {response.text[:100]}{Style.RESET_ALL}")
                return False
                
        except requests.ConnectionError:
            print(f"{Fore.YELLOW}[SSH] Backend unavailable, will retry...{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}[SSH Error] {e}{Style.RESET_ALL}")
            return False

    def stop(self):
        """Stop the monitor."""
        self._running = False


def main():
    parser = argparse.ArgumentParser(description="AuthSentinel Collector with SSH Monitoring")
    parser.add_argument("--backend", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--label", default="LAPTOP-A", help="Machine label")
    
    args = parser.parse_args()
    
    print(f"{Fore.CYAN}╔════════════════════════════════════════╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║  AuthSentinel SSH Event Forwarder      ║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╚════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"Backend: {args.backend}")
    print(f"Label: {args.label}")
    print()
    
    forwarder = SSHEventForwarder(args.backend, args.label)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")
        forwarder.stop()


if __name__ == "__main__":
    main()
