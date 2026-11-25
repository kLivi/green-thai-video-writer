#!/usr/bin/env python3
import base64, os, sys
from pathlib import Path
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, str(Path.home() / "Documents/green-energy-thailand/shared"))
from env_loader import load_env

env = load_env()
url = (os.environ.get("WORDPRESS_URL") or env.get("WORDPRESS_URL", "")).rstrip("/")
user = os.environ.get("WORDPRESS_USERNAME") or env.get("WORDPRESS_USERNAME", "")
password = (os.environ.get("WORDPRESS_APP_PASSWORD") or env.get("WORDPRESS_APP_PASSWORD", "")).replace(" ", "")
auth = {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}

image_path = Path("output/images/thailand-data-centers-green-power-featured.webp")
headers = {
    **auth,
    "Content-Disposition": f'attachment; filename="{image_path.name}"',
    "Content-Type": "image/webp",
}

with open(image_path, "rb") as f:
    resp = requests.post(f"{url}/wp-json/wp/v2/media", headers=headers, data=f.read(), timeout=60)

if resp.status_code not in (200, 201):
    print("Upload failed:", resp.status_code, resp.text[:300])
    sys.exit(1)

media = resp.json()
media_id = media["id"]
print(f"Uploaded cover image ID: {media_id}")

# Update post featured media
update_resp = requests.post(f"{url}/wp-json/wp/v2/posts/1052", headers=auth, json={"featured_media": media_id}, timeout=30)
if update_resp.status_code in (200, 201):
    print("Updated post 1052 featured image to cover.")
else:
    print("Update failed:", update_resp.status_code, update_resp.text[:300])
