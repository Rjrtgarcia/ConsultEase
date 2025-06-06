#!/usr/bin/env python3
"""
MQTT Broker Auto-Detection Utility for ConsultEase Central System.

This module automatically detects the MQTT broker address, prioritizing localhost
and providing fallback options for different network configurations.
"""

import socket
import subprocess
import logging
import time
import paho.mqtt.client as mqtt
from typing import List, Optional, Tuple
import threading

logger = logging.getLogger(__name__)


class MQTTBrokerDetector:
    """
    Automatically detect MQTT broker address with multiple strategies.
    """
    
    def __init__(self, port: int = 1883, timeout: int = 3):
        """
        Initialize the MQTT broker detector.
        
        Args:
            port: MQTT port to check (default 1883)
            timeout: Connection timeout in seconds
        """
        self.port = port
        self.timeout = timeout
        
        # Priority order for broker detection
        self.candidate_hosts = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",  # Listen on all interfaces
        ]
        
        # Network discovery candidates (will be populated dynamically)
        self.network_candidates = []
        
    def detect_broker(self) -> Optional[str]:
        """
        Detect MQTT broker using multiple strategies.
        
        Returns:
            str: MQTT broker host address, or None if not found
        """
        logger.info("🔍 Starting MQTT broker auto-detection...")
        
        # Strategy 1: Check localhost/loopback first (central system is broker)
        broker = self._check_localhost_brokers()
        if broker:
            logger.info(f"✅ Found local MQTT broker at: {broker}")
            return broker
        
        # Strategy 2: Check local network interfaces
        broker = self._check_network_interfaces()
        if broker:
            logger.info(f"✅ Found MQTT broker on local network: {broker}")
            return broker
        
        # Strategy 3: Network discovery scan
        broker = self._network_discovery()
        if broker:
            logger.info(f"✅ Found MQTT broker via network scan: {broker}")
            return broker
        
        logger.warning("❌ No MQTT broker found via auto-detection")
        return None
    
    def _check_localhost_brokers(self) -> Optional[str]:
        """Check localhost and loopback addresses."""
        localhost_candidates = ["localhost", "127.0.0.1"]
        
        for host in localhost_candidates:
            if self._test_connection(host):
                return host
        
        return None
    
    def _check_network_interfaces(self) -> Optional[str]:
        """Check local network interface addresses."""
        try:
            # Get local IP addresses
            local_ips = self._get_local_ip_addresses()
            
            for ip in local_ips:
                if self._test_connection(ip):
                    return ip
            
        except Exception as e:
            logger.debug(f"Error checking network interfaces: {e}")
        
        return None
    
    def _network_discovery(self) -> Optional[str]:
        """Perform network discovery to find MQTT brokers."""
        try:
            # Get local network subnets
            subnets = self._get_local_subnets()
            
            # Common MQTT broker addresses in typical networks
            common_addresses = []
            for subnet in subnets:
                # Add common router/server addresses
                base = ".".join(subnet.split(".")[:-1])
                common_addresses.extend([
                    f"{base}.1",    # Router
                    f"{base}.100",  # Common server IP
                    f"{base}.101",
                    f"{base}.3",    # Your configured ESP32 target
                ])
            
            # Test common addresses first
            for host in common_addresses:
                if self._test_connection(host):
                    return host
            
            # If common addresses fail, do a limited subnet scan
            return self._limited_subnet_scan(subnets)
            
        except Exception as e:
            logger.debug(f"Error in network discovery: {e}")
        
        return None
    
    def _test_connection(self, host: str) -> bool:
        """
        Test if a host has an MQTT broker running.
        
        Args:
            host: Host to test
            
        Returns:
            bool: True if MQTT broker is accessible
        """
        try:
            # First, test socket connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, self.port))
            sock.close()
            
            if result == 0:
                # Socket connection successful, now test MQTT
                return self._test_mqtt_connection(host)
            
        except Exception as e:
            logger.debug(f"Connection test failed for {host}:{self.port} - {e}")
        
        return False
    
    def _test_mqtt_connection(self, host: str) -> bool:
        """
        Test MQTT connection to a host.
        
        Args:
            host: Host to test
            
        Returns:
            bool: True if MQTT connection successful
        """
        try:
            client = mqtt.Client("BrokerDetector_" + str(int(time.time())))
            
            # Use a simple connection test
            connected = False
            
            def on_connect(client, userdata, flags, rc):
                nonlocal connected
                connected = (rc == 0)
            
            client.on_connect = on_connect
            client.connect(host, self.port, 5)  # 5 second timeout
            
            # Wait for connection
            start_time = time.time()
            client.loop_start()
            
            while not connected and (time.time() - start_time) < self.timeout:
                time.sleep(0.1)
            
            client.loop_stop()
            client.disconnect()
            
            return connected
            
        except Exception as e:
            logger.debug(f"MQTT connection test failed for {host}: {e}")
            return False
    
    def _get_local_ip_addresses(self) -> List[str]:
        """Get all local IP addresses."""
        ip_addresses = []
        
        try:
            # Get hostname and resolve to IPs
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            ip_addresses.extend(local_ips)
            
            # Alternative method using socket connection
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to a remote address to get local IP
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                if local_ip not in ip_addresses:
                    ip_addresses.append(local_ip)
                    
        except Exception as e:
            logger.debug(f"Error getting local IP addresses: {e}")
        
        # Remove localhost addresses (already checked)
        ip_addresses = [ip for ip in ip_addresses if not ip.startswith("127.")]
        
        return ip_addresses
    
    def _get_local_subnets(self) -> List[str]:
        """Get local network subnets."""
        subnets = []
        
        try:
            local_ips = self._get_local_ip_addresses()
            
            for ip in local_ips:
                # Assume /24 subnet for simplicity
                subnet = ".".join(ip.split(".")[:-1]) + ".0"
                if subnet not in subnets:
                    subnets.append(subnet)
                    
        except Exception as e:
            logger.debug(f"Error getting local subnets: {e}")
        
        return subnets
    
    def _limited_subnet_scan(self, subnets: List[str]) -> Optional[str]:
        """
        Perform a limited scan of network subnets.
        
        Args:
            subnets: List of subnet addresses to scan
            
        Returns:
            str: First found MQTT broker, or None
        """
        logger.info("🔍 Performing limited network scan for MQTT brokers...")
        
        # Scan only common server IP ranges to avoid flooding the network
        scan_ranges = [
            range(1, 10),      # 192.168.1.1 - 192.168.1.9 (routers, gateways)
            range(100, 110),   # 192.168.1.100 - 192.168.1.109 (servers)
            range(200, 210),   # 192.168.1.200 - 192.168.1.209 (servers)
        ]
        
        for subnet in subnets:
            base = ".".join(subnet.split(".")[:-1])
            
            for scan_range in scan_ranges:
                for host_num in scan_range:
                    host = f"{base}.{host_num}"
                    
                    if self._test_connection(host):
                        logger.info(f"✅ Found MQTT broker at {host}")
                        return host
        
        return None


def auto_detect_mqtt_broker(port: int = 1883, timeout: int = 3) -> str:
    """
    Convenience function to auto-detect MQTT broker.
    
    Args:
        port: MQTT port (default 1883)
        timeout: Connection timeout in seconds
        
    Returns:
        str: MQTT broker host address (defaults to localhost if not found)
    """
    detector = MQTTBrokerDetector(port, timeout)
    broker = detector.detect_broker()
    
    if broker:
        logger.info(f"✅ Auto-detected MQTT broker: {broker}")
        return broker
    else:
        logger.warning("⚠️ Could not auto-detect MQTT broker, falling back to localhost")
        return "localhost"


def get_optimal_mqtt_config() -> dict:
    """
    Get optimal MQTT configuration with auto-detected broker.
    
    Returns:
        dict: MQTT configuration
    """
    broker_host = auto_detect_mqtt_broker()
    
    config = {
        "broker_host": broker_host,
        "broker_port": 1883,
        "keepalive": 60,
        "client_id": "consultease_central_auto",
        "auto_detected": True
    }
    
    logger.info(f"📋 Optimal MQTT config: {config}")
    return config


def verify_broker_connectivity(host: str, port: int = 1883) -> Tuple[bool, str]:
    """
    Verify connectivity to a specific MQTT broker.
    
    Args:
        host: MQTT broker host
        port: MQTT broker port
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        detector = MQTTBrokerDetector(port)
        
        if detector._test_connection(host):
            return True, f"✅ Successfully connected to MQTT broker at {host}:{port}"
        else:
            return False, f"❌ Cannot connect to MQTT broker at {host}:{port}"
            
    except Exception as e:
        return False, f"❌ Error testing MQTT broker {host}:{port}: {e}"


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 MQTT Broker Auto-Detection Test")
    print("=" * 50)
    
    # Test auto-detection
    broker = auto_detect_mqtt_broker()
    print(f"Detected broker: {broker}")
    
    # Test optimal config
    config = get_optimal_mqtt_config()
    print(f"Optimal config: {config}")
    
    # Verify connectivity
    success, message = verify_broker_connectivity(broker)
    print(message) 