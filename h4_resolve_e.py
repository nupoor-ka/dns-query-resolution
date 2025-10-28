import time
import subprocess
import os
import sys

DNS_IP = '10.0.0.5'
HOST_NAME = 'h4'
URL_FILE = f'/home/mininet/dns-query-resolution/{HOST_NAME.upper()}_urls.txt'
RECURSIVE_MODE = True   # 🔁 change to False for RD=0 (non-recursive)

print(f"starting url resolution process for {HOST_NAME}")
print(f"recursion mode = {'ON (RD=1)' if RECURSIVE_MODE else 'OFF (RD=0)'}")

def run_cmd(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=20)
        if result.returncode != 0 and result.stderr:
            print(f"command error: {command}\n{result.stderr.strip()}", file=sys.stderr)
        return result.stdout.strip()
    except Exception as e:
        print(f"execution failed for command: {command}. error: {e}", file=sys.stderr)
        return ""

def resolve_urls_dig(url_file, dns_ip, recursive):
    try:
        with open(url_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"url file not found for {HOST_NAME}", file=sys.stderr)
        return 0, 0, 0, 0

    success = 0
    fail = 0
    total_time = 0.0
    print(f"\nresolving {len(urls)} URLs for {HOST_NAME} using DNS {dns_ip}...")

    dig_flag = "" if recursive else "+norecurse"

    for i, url in enumerate(urls, start=1):
        start = time.time()
        command = f'dig @{dns_ip} {url} +short {dig_flag} +time=18 +tries=2'
        result = run_cmd(command)
        latency = time.time() - start
        if result and ('connection timed out' not in result.lower()):
            success += 1
            total_time += latency
        else:
            fail += 1
        if i % 20 == 0:
            print(f"{HOST_NAME}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

os.system(f'echo nameserver {DNS_IP} > /etc/resolv.conf')
print(f"configured nameserver to {DNS_IP}")

avg_latency, throughput, success, fail = resolve_urls_dig(URL_FILE, DNS_IP, RECURSIVE_MODE)
print(f"\nresults for {HOST_NAME}:")
print(f"average latency: {avg_latency:.3f} s")
print(f"throughput: {throughput:.3f} queries/sec")
print(f"successful: {success}, failed: {fail}")
