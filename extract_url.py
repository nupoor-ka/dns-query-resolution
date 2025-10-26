import pandas as pd
import re

def extract_urls_from_csv(file_path):
    df = pd.read_csv(file_path)
    domain_pattern = re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b') # getting domain names
    urls = []
    for info in df['Info']:
        if isinstance(info, str):
            urls.extend(domain_pattern.findall(info))
    ignore = {'wpad', 'isatap', 'local', 'isilon'} # removing some local network entries
    unique_urls = sorted({u for u in urls if u.split('.')[0].lower() not in ignore})

    output_path = file_path.replace('.csv', '.txt')
    with open(output_path, 'w') as f:
        for url in unique_urls:
            f.write(url + '\n')
    print(f"\nextracted {len(unique_urls)} URLs and saved to {output_path}")

if __name__ == "__main__":
    for i in range(1,5):
        file_path = f"H{i}_urls.csv"
        extract_urls_from_csv(file_path)
