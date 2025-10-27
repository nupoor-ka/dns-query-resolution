import time
def resolve_urls(host, url_file):
    #Returns avg_latency, throughput, success_count, fail_count
    
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]#obtaining the urls from the filtered pcaps

    success = 0
    fail = 0
    total_time = 0.0
    ran = 0
    for url in urls:
        ran+=1
        start = time.time()
        result = host.cmd(f'dig +short {url}') #returns the ip address of the url
        latency = time.time() - start

        if(ran%20==0): print(f"{ran} done") #check to ensure files are running

        if (not result.strip()) or (result.strip()[2:].isalpha()):#if not a valid url then this
            fail+=1
        else:
            success += 1
            total_time += latency

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0

    return avg_latency, throughput, success, fail
