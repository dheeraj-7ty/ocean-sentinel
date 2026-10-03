import json
import httpx

dois = ['10.5281/zenodo.14279466', '10.5281/zenodo.15298010', '10.5281/zenodo.4672426']
for d in dois:
    record_id = d.split('.')[-1]
    url = f"https://zenodo.org/api/records/{record_id}"
    r = httpx.get(url, timeout=15)
    print(f"\n==========================================")
    print(f"=== Record ID: {record_id} ({d}) ===")
    print(f"==========================================")
    if r.status_code == 200:
        data = r.json()
        meta = data.get("metadata", {})
        print("Title:", meta.get("title"))
        print("Pub date:", meta.get("publication_date"))
        print("Creators:", [c.get("name") for c in meta.get("creators", [])])
        print("Keywords:", meta.get("keywords"))
        print("License:", meta.get("license"))
        desc = meta.get("description", "")
        # Strip HTML tags simply
        import re
        clean_desc = re.sub('<[^<]+?>', '', desc)
        print("Description:", clean_desc[:800])
        files = data.get("files", [])
        print(f"Files count: {len(files)}")
        for f in files[:8]:
            print(f"  - {f.get('key')} ({f.get('size')} bytes)")
    else:
        print("Failed to retrieve:", r.status_code)
