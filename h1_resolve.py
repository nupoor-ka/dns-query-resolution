from mininet.net import Mininet
import time

# Connect to existing Mininet network
net = Mininet(init=False)
net.start()  # attach to already running net

# --- Choose the host and URL file ---
host_name = 'h1'  # change to h2, h3, h4 as needed
url_file = f'/home/mininet/dns-query-resolution/{host_name.upper()}_urls.txt'
dns_ip = '10.0.0.5'  # your custom DNS server’s IP

# --- Get host object ---
host = net.get(host_name)

# --- Ensure resolv.conf points to custom DNS ---
host.cmd(f'sh -c "echo nameserver {dns_ip} > /etc/resolv.conf"')

# --- Function to resolve URLs using dig ---
def resolve_urls_dig(host, url_file, dns_ip):
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    success = 0
    fail = 0
    total_time = 0.0

    for i, url in enumerate(urls, start=1):
        start = time.time()
        result = host.cmd(f'dig @{dns_ip} {url} +short')
        latency = time.time() - start

        if result.strip():
            success += 1
            total_time += latency
        else:
            fail += 1

        if i % 20 == 0:
            print(f"{host.name}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

# --- Run the resolver for this host ---
print(f"\nResolving URLs for {host_name} using DNS {dns_ip}...")
avg_latency, throughput, success, fail = resolve_urls_dig(host, url_file, dns_ip)

print(f"\nResults for {host_name.upper()}:")
print(f"Average Latency: {avg_latency:.3f} s")
print(f"Throughput: {throughput:.2f} queries/sec")
print(f"Successful: {success}, Failed: {fail}")

net.stop()
