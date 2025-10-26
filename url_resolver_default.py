import time
import random

def resolve_urls(host, url_file):
    """
    Resolve URLs from a text file using the host's default resolver.
    Returns: avg_latency, throughput, success_count, fail_count
    """
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    success = 0
    fail = 0
    total_time = 0.0
    c=0
    ran = 0
    nums = random.sample(range(100), 40)
    for url in urls:
        if c not in nums:
            c+=1
            continue
        ran+=1
        start = time.time()
        result = host.cmd(f'dig +short {url}')
        if(ran%5==0): print(f"{ran*2.5} done")
        latency = time.time() - start
        if result.strip():
            success += 1
            total_time += latency
        else:
            fail += 1
        c+=1

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0

    return avg_latency, throughput, success*2.5, fail*2.5
