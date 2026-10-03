"""Discovery script for external oil spill and look-alike SAR benchmarks.

Queries Zenodo API, arXiv API, and PANGAEA/literature metadata to find
candidate datasets for Phase 7B.0 evaluation.
"""

import json
import time
from pathlib import Path
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent

def search_zenodo(query: str, size: int = 15):
    url = "https://zenodo.org/api/records"
    headers = {"User-Agent": "OceanSentinel-Research/1.0 (academic audit)"}
    params = {"q": query, "size": size, "sort": "bestmatch"}
    try:
        r = httpx.get(url, params=params, headers=headers, timeout=20.0)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Zenodo error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"Zenodo request failed: {e}")
    return None

def search_arxiv(query: str, max_results: int = 10):
    import urllib.parse
    import xml.etree.ElementTree as ET
    base_url = "http://export.arxiv.org/api/query"
    params = f"?search_query={urllib.parse.quote(query)}&start=0&max_results={max_results}&sortBy=relevance"
    try:
        r = httpx.get(base_url + params, timeout=20.0)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = []
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                id_url = entry.find("atom:id", ns).text.strip()
                published = entry.find("atom:published", ns).text.strip()
                entries.append({"title": title, "summary": summary, "url": id_url, "published": published})
            return entries
    except Exception as e:
        print(f"arXiv request failed: {e}")
    return []

def main():
    print("Searching Zenodo for Sentinel-1 oil spill and look-alike datasets...")
    queries = [
        'Sentinel-1 "oil spill" "look-alike"',
        'Sentinel-1 "oil slick" dataset',
        'SAR "look-alike" "oil spill" dataset',
        '"TenGeoP-SARwv" OR "SAR-Ocean"',
        'UAVSAR "oil spill" dataset',
        'oil spill segmentation SAR dataset',
    ]

    results = {}
    for q in queries:
        print(f"\n--- Zenodo Query: {q} ---")
        z = search_zenodo(q, size=8)
        if z and "hits" in z:
            hits = z["hits"].get("hits", [])
            print(f"Hits: {len(hits)} (Total: {z['hits'].get('total')})")
            for h in hits:
                meta = h.get("metadata", {})
                title = meta.get("title")
                doi = h.get("doi") or meta.get("doi")
                url = h.get("links", {}).get("html")
                pub_date = meta.get("publication_date")
                desc = meta.get("description", "")[:250]
                results[title] = {
                    "source": "Zenodo",
                    "title": title,
                    "doi": doi,
                    "url": url,
                    "publication_date": pub_date,
                    "description": desc,
                    "keywords": meta.get("keywords", []),
                }
                print(f"  * [{pub_date}] {title} (DOI: {doi})")
        time.sleep(1)

    print("\n\nSearching arXiv for recent 2024-2026 SAR oil spill / look-alike papers...")
    arxiv_queries = [
        'all:"Sentinel-1" AND all:"oil spill" AND all:"look-alike"',
        'all:"SAR" AND all:"oil slick" AND all:"segmentation dataset"',
        'all:"UAVSAR" AND all:"oil spill"',
    ]
    arxiv_results = []
    for q in arxiv_queries:
        print(f"\n--- arXiv Query: {q} ---")
        entries = search_arxiv(q, max_results=5)
        for e in entries:
            print(f"  * [{e['published'][:10]}] {e['title']} ({e['url']})")
            arxiv_results.append(e)
        time.sleep(1)

    out_file = REPO_ROOT / "scratch" / "external_dataset_search_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"zenodo_candidates": list(results.values()), "arxiv_papers": arxiv_results}, f, indent=2)
    print(f"\nWrote search results to: {out_file}")

if __name__ == "__main__":
    main()
