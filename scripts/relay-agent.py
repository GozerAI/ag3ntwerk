#!/usr/bin/env python3
"""
ag3ntwerk Relay Agent — Local network bridge for cloud-hosted ag3ntwerk.

Install on one trusted machine inside your local network. It opens an
outbound WebSocket tunnel to your cloud-hosted ag3ntwerk instance and
executes fleet operations (discovery, provisioning, deployment) locally.

Usage:
    # First, generate a token on your cloud ag3ntwerk:
    #   curl -X POST https://your-vps.com/api/v1/fleet/relays/token \
    #     -H "Content-Type: application/json" \
    #     -d '{"relay_name": "office-relay", "created_by": "admin"}'

    # Then run this agent:
    python relay-agent.py \
        --controller-url wss://your-vps.com \
        --token ag3ntwerk-relay-... \
        --name office-relay \
        --networks 192.168.1.0/24 10.0.0.0/24

    # Or with environment variables:
    AGENTWERK_CONTROLLER_URL=wss://your-vps.com \
    AGENTWERK_RELAY_TOKEN=ag3ntwerk-relay-... \
    AGENTWERK_RELAY_NAME=office-relay \
    AGENTWERK_RELAY_NETWORKS=192.168.1.0/24,10.0.0.0/24 \
    python relay-agent.py

Requirements:
    pip install websockets
"""

import argparse
import asyncio
import os
import sys

# Add the src directory to path so we can import ag3ntwerk modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, "src"))


def main():
    parser = argparse.ArgumentParser(
        description="ag3ntwerk Relay Agent — bridge your local network to cloud ag3ntwerk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --controller-url wss://ag3ntwerk.example.com --token ag3ntwerk-relay-abc123 --networks 192.168.1.0/24
  %(prog)s -u wss://my-vps:3737 -t ag3ntwerk-relay-abc123 -n home-lab -N 192.168.1.0/24 10.0.0.0/8
        """,
    )
    parser.add_argument(
        "-u",
        "--controller-url",
        default=os.environ.get("AGENTWERK_CONTROLLER_URL", ""),
        help="WebSocket URL of your cloud ag3ntwerk (e.g. wss://ag3ntwerk.example.com)",
    )
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ.get("AGENTWERK_RELAY_TOKEN", ""),
        help="Relay authentication token (from /api/v1/fleet/relays/token)",
    )
    parser.add_argument(
        "-n",
        "--name",
        default=os.environ.get("AGENTWERK_RELAY_NAME", ""),
        help="Human-readable name for this relay (default: hostname)",
    )
    parser.add_argument(
        "-N",
        "--networks",
        nargs="*",
        default=None,
        help="Local network CIDRs this relay can reach (e.g. 192.168.1.0/24)",
    )
    parser.add_argument(
        "--reconnect-interval",
        type=float,
        default=5.0,
        help="Base reconnect interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--max-reconnect-delay",
        type=float,
        default=300.0,
        help="Maximum reconnect delay in seconds (default: 300)",
    )

    args = parser.parse_args()

    # Resolve networks from args or env
    networks = args.networks
    if networks is None:
        env_networks = os.environ.get("AGENTWERK_RELAY_NETWORKS", "")
        networks = [n.strip() for n in env_networks.split(",") if n.strip()]

    if not args.controller_url:
        parser.error("Controller URL required. Set --controller-url or AGENTWERK_CONTROLLER_URL")

    if not args.token:
        parser.error(
            "Relay token required. Set --token or AGENTWERK_RELAY_TOKEN.\n"
            "Generate one on your cloud ag3ntwerk:\n"
            "  curl -X POST https://your-vps/api/v1/fleet/relays/token "
            '-H "Content-Type: application/json" '
            '-d \'{"relay_name": "my-relay", "created_by": "admin"}\''
        )

    if not networks:
        print(
            "WARNING: No networks specified. The relay won't know which "
            "local networks it can reach.\n"
            "Add --networks 192.168.1.0/24 or set AGENTWERK_RELAY_NETWORKS",
            file=sys.stderr,
        )

    # Import and run the relay agent
    from ag3ntwerk.modules.distributed.relay import RelayAgent

    agent = RelayAgent(
        controller_url=args.controller_url,
        token=args.token,
        name=args.name,
        networks=networks,
        reconnect_interval=args.reconnect_interval,
        max_reconnect_delay=args.max_reconnect_delay,
    )

    print(f"ag3ntwerk Relay Agent")
    print(f"  Name:       {agent.name}")
    print(f"  Controller: {args.controller_url}")
    print(f"  Networks:   {', '.join(networks) if networks else '(none)'}")
    print(f"  Connecting...")
    print()

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\nRelay agent stopped.")


if __name__ == "__main__":
    main()
