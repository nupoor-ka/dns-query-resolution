import time
import subprocess
import os
import sys
# decided to do just cli automation instead of automating everything as that wasn't working
HOST_NAME = 'h3'
URL_FILE = f'/home/mininet/dns-query-resolution/{HOST_NAME.upper()}_urls.txt'
print(f"starting url resolution process using default resolver for {HOST_NAME}")
def run_cmd(command): # to run command in shell
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=20
        )
        if result.returncode != 0 and result.stderr: # command failed
            print(f"command error: {command}\n{result.stderr.strip()}", file=sys.stderr)
        return result.stdout.strip()
    except Exception as e:
        print(f"execution failed for command: {command}. error: {e}", file=sys.stderr)
        return ""

def resolve_urls_dig(url_file):
    try:
        with open(url_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"url file not found for {HOST_NAME}, check path", file=sys.stderr)
        return 0, 0, 0, 0
    
    success = 0
    fail = 0
    total_time = 0.0

    print(f"\nresolving {len(urls)} URLs for {HOST_NAME} using default resolver")

    for i, url in enumerate(urls, start=1): # for every url
        start = time.time()
        command = f'dig {url} +short' # short response, timeout 4 seconds, no retries
        result = run_cmd(command)
        latency = time.time() - start
        if result and ('connection timed out' not in result.lower()): # get empty or ;; connection timed out if it doesn't work
            success += 1
            total_time += latency
        else:
            fail += 1

        if i % 20 == 0:
            print(f"{HOST_NAME}: {i} queries processed")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

avg_latency, throughput, success, fail = resolve_urls_dig(URL_FILE)
print(f"\nresults for {HOST_NAME}:")
print(f"average latency: {avg_latency:.3f} s")
print(f"throughput: {throughput:.3f} queries/sec")
print(f"successful: {success}, failed: {fail}")
