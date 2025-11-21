import os
import requests
from concurrent.futures import ThreadPoolExecutor

SUPABASE_URL = "https://<your>.supabase.co"
BUCKET = "models"
API_KEY = "<service_role_key>"

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
}

ROOT = "backend/backend/models"

def upload(local_path, remote_path):
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{remote_path}"
    with open(local_path, "rb") as f:
        data = f.read()
    r = requests.post(url, headers=HEADERS, data=data)
    print(f"{remote_path}: {r.status_code}")
    return r.status_code


def gather_files():
    out = []
    for root, dirs, files in os.walk(ROOT):
        for f in files:
            if f.endswith((".joblib", ".keras", ".pkl")):
                local = os.path.join(root, f)
                rel = os.path.relpath(local, ROOT).replace("\\", "/")
                out.append((local, rel))
    return out


pairs = gather_files()
print("Files:", len(pairs))

with ThreadPoolExecutor(max_workers=20) as ex:
    for local, remote in pairs:
        ex.submit(upload, local, remote)
