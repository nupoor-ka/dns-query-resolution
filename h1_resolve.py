import time
import subprocess
import os
import sys

# --- Constants (These should be manually configured in the Mininet CLI before running this script) ---
# NOTE: The DNS_IP must be manually configured to 10.0.0.5 in the Mininet CLI BEFORE running this script.
DNS_IP = '10.0.0.5' 
HOST_NAME = 'h1'  # This script assumes it is running on 'h1'
URL_FILE = f'/home/mininet/dns-query-resolution/{HOST_NAME.upper()}_urls.txt'

def run_cmd(command):
    """Executes a shell command in the current host's namespace and returns stdout."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10 # Set a generous timeout for network queries
        )
        # For error debugging: print stderr if the command failed
        if result.returncode != 0 and result.stderr:
            print(f"Command Error: {command}\n{result.stderr.strip()}", file=sys.stderr)
        return result.stdout.strip()
    except Exception as e:
        print(f"Execution failed for command: {command}. Error: {e}", file=sys.stderr)
        return ""

def resolve_urls_dig(url_file, dns_ip):
    """Reads URLs and performs DNS resolution, calculating metrics."""
    try:
        with open(url_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"ERROR: URL file not found at {url_file}. Check path.", file=sys.stderr)
        return 0, 0, 0, 0
    
    success = 0
    fail = 0
    total_time = 0.0

    print(f"\nResolving {len(urls)} URLs for {HOST_NAME} using DNS {dns_ip}...")

    # The dig command targets the custom DNS server
    for i, url in enumerate(urls, start=1):
        start = time.time()
        
        # Use +time=2 +tries=1 to ensure a consistent, measurable attempt
        command = f'dig @{dns_ip} {url} +short +time=2 +tries=1'
        result = run_cmd(command)
        latency = time.time() - start

        # Success: Result is not empty and is not a simple error message
        if result and not result.lower().startswith('connection timed out'):
            success += 1
            total_time += latency
        else:
            fail += 1

        if i % 20 == 0:
            print(f"{HOST_NAME}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

# --- Main Execution ---

# 1. Ensure resolv.conf points to the custom DNS (if not done manually in CLI)
# This uses os.system because it's a simple shell command that doesn't need output captured.
os.system(f'echo nameserver {DNS_IP} > /etc/resolv.conf')
print(f"Configured nameserver to {DNS_IP}")

# 2. Run the resolver
avg_latency, throughput, success, fail = resolve_urls_dig(URL_FILE, DNS_IP)

# 3. Print Results
print(f"\nResults for {HOST_NAME.upper()}:")
print(f"Average Latency: {avg_latency:.3f} s")
print(f"Throughput: {throughput:.2f} queries/sec")
print(f"Successful: {success}, Failed: {fail}")