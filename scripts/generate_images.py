"""One-off image generation for the Bangchak SAF article. Reads the API key
via the shared env loader (never printed), submits all jobs, polls, downloads,
resizes to WebP.
"""
import sys
import time
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))
from env_loader import get_secret

API_KEY = get_secret("IMAGE_API_KEY")
OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "images"
SLUG = "thailand-first-saf-plant-bangchak-cooking-oil-jet-fuel"

JOBS = [
    ("featured", "A commercial jet aircraft being refueled by a tanker truck on an airport tarmac, overcast daylight, Bangkok, natural lighting, candid photo, realistic", 1200, 630),
    ("jerrycans", "Stacked plastic jerry cans of used cooking oil outside a small Thai restaurant kitchen, morning light, candid photo, realistic", 650, 366),
    ("pouring", "A person pouring used cooking oil from a wok into a plastic collection jug at a home kitchen counter, overcast daylight, candid photo, realistic", 450, 600),
    ("dashboard", "A laptop screen showing a carbon trading dashboard with bar charts, on a plain office desk, natural window light, candid photo, realistic", 550, 550),
]

HEADERS = {"Authorization": f"Key {API_KEY}", "Content-Type": "application/json"}


def submit(prompt, w, h):
    r = requests.post(
        "https://queue.fal.run/fal-ai/bytedance/seedream/v4.5/text-to-image",
        headers=HEADERS,
        json={"prompt": prompt, "image_size": {"width": w, "height": h}, "num_images": 1},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def poll(status_url):
    while True:
        r = requests.get(status_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "COMPLETED":
            return
        time.sleep(5)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    submitted = []
    for descriptor, prompt, w, h in JOBS:
        job = submit(prompt, w, h)
        submitted.append((descriptor, w, h, job["status_url"], job["response_url"]))
        print(f"submitted {descriptor}")

    for descriptor, w, h, status_url, response_url in submitted:
        poll(status_url)
        r = requests.get(response_url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        result = r.json()
        img_url = result["images"][0]["url"]
        raw = requests.get(img_url, timeout=60).content
        raw_path = Path(f"/tmp/img_{descriptor}.png")
        raw_path.write_bytes(raw)

        img = Image.open(raw_path).convert("RGB")
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        name = f"{SLUG}-featured.webp" if descriptor == "featured" else f"{SLUG}-{descriptor}.webp"
        out_path = OUT_DIR / name
        img.save(out_path, "WEBP", quality=82)
        print(f"saved {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
