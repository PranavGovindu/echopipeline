#!/usr/bin/env python3
"""
Run VibeVoice server with Cloudflare Tunnel for public access.

This script starts the VibeVoice server and creates a Cloudflare Tunnel,
giving you a public URL (e.g., https://xxxxx.trycloudflare.com)
"""

import argparse
import os
import re
import subprocess
import sys
import time
import threading
from pathlib import Path

def download_cloudflared():
    """Download cloudflared binary if not present."""
    cloudflared_path = Path("cloudflared")
    
    if cloudflared_path.exists():
        print("✅ cloudflared already exists")
        return cloudflared_path
    
    print("📥 Downloading cloudflared...")
    
    import platform
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
        elif machine in ["aarch64", "arm64"]:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
        else:
            print(f"❌ Unsupported architecture: {machine}")
            sys.exit(1)
    elif system == "darwin":  # macOS
        if machine == "arm64":
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64"
        else:
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64"
    else:
        print(f"❌ Unsupported OS: {system}")
        sys.exit(1)
    
    try:
        import urllib.request
        urllib.request.urlretrieve(url, "cloudflared")
        cloudflared_path.chmod(0o755)
        print("✅ Downloaded cloudflared")
        return cloudflared_path
    except Exception as e:
        print(f"❌ Failed to download cloudflared: {e}")
        print("💡 You can manually download from: https://github.com/cloudflare/cloudflared/releases")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run VibeVoice server with Cloudflare Tunnel"
    )
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument(
        "--model_path",
        type=str,
        default="microsoft/VibeVoice-Realtime-0.5B",
        help="Model path or HuggingFace ID",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=["cpu", "cuda", "mps"],
        help="Device to use",
    )
    parser.add_argument(
        "--no-cloudflare",
        action="store_true",
        help="Run server without Cloudflare Tunnel",
    )
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["MODEL_PATH"] = args.model_path
    os.environ["MODEL_DEVICE"] = args.device
    
    # Start VibeVoice server
    print(f"🚀 Starting VibeVoice server on port {args.port}...")
    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "web.app:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.port),
    ]
    
    server_process = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    server_ready = False
    public_url = None
    
    def read_server_output():
        nonlocal server_ready
        for line in server_process.stdout:
            print(f"[SERVER] {line.rstrip()}")
            if "Uvicorn running on" in line or "Application startup complete" in line:
                server_ready = True
                print("✅ VibeVoice server is ready!")
    
    # Start reading server output
    server_thread = threading.Thread(target=read_server_output, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    print("⏳ Waiting for server to start...")
    timeout = 30
    elapsed = 0
    while not server_ready and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5
        if server_process.poll() is not None:
            print("❌ Server process exited unexpectedly")
            sys.exit(1)
    
    if not server_ready:
        print("⚠️  Server may not be ready yet, continuing anyway...")
    
    if args.no_cloudflare:
        print(f"\n✅ Server running at: http://localhost:{args.port}")
        print("Press Ctrl+C to stop")
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            server_process.terminate()
        return
    
    # Start Cloudflare Tunnel
    print("\n🌐 Starting Cloudflare Tunnel...")
    cloudflared_path = download_cloudflared()
    
    tunnel_cmd = [
        str(cloudflared_path),
        "tunnel",
        "--url",
        f"http://localhost:{args.port}",
        "--no-autoupdate",
    ]
    
    tunnel_process = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    url_pattern = re.compile(r"(https://[a-z0-9-]+\.trycloudflare\.com)")
    
    def read_tunnel_output():
        nonlocal public_url
        for line in tunnel_process.stdout:
            print(f"[TUNNEL] {line.rstrip()}")
            match = url_pattern.search(line)
            if match:
                public_url = match.group(1)
                print(f"\n{'='*60}")
                print(f"✅ PUBLIC URL: {public_url}")
                print(f"{'='*60}")
                print(f"\n📋 Use this URL in your Pipecat Cloud secrets:")
                print(f"   VIBEVOICE_SERVER_URL={public_url.replace('https://', 'wss://')}")
                print(f"\n💡 Note: Replace 'https://' with 'wss://' for WebSocket")
                print(f"   Example: wss://xxxxx.trycloudflare.com")
                print(f"\n⚠️  This URL is temporary and will change on restart")
                print(f"   For production, use a permanent tunnel or domain")
    
    tunnel_thread = threading.Thread(target=read_tunnel_output, daemon=True)
    tunnel_thread.start()
    
    # Wait for tunnel URL
    print("⏳ Waiting for Cloudflare Tunnel URL...")
    timeout = 30
    elapsed = 0
    while not public_url and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5
        if tunnel_process.poll() is not None:
            print("❌ Tunnel process exited unexpectedly")
            server_process.terminate()
            sys.exit(1)
    
    if not public_url:
        print("⚠️  Could not get Cloudflare Tunnel URL")
        print("💡 Check cloudflared output above for errors")
    
    print("\n✅ Both server and tunnel are running!")
    print("Press Ctrl+C to stop both services")
    
    try:
        # Wait for either process to exit
        while True:
            if server_process.poll() is not None:
                print("\n❌ Server process exited")
                tunnel_process.terminate()
                break
            if tunnel_process.poll() is not None:
                print("\n❌ Tunnel process exited")
                server_process.terminate()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        server_process.terminate()
        tunnel_process.terminate()
        print("✅ Stopped")


if __name__ == "__main__":
    main()

