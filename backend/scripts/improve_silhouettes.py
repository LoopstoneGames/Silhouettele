"""Improve WEAK silhouettes: pull multiple candidate images from Wikimedia
Commons, build a silhouette from each, score for 'cleanliness' (one dominant
connected shape, light base), and keep the best. Saves to scripts/review/ for
visual verification BEFORE overwriting the live images.

Run:  python scripts/improve_silhouettes.py            # generate candidates
      python scripts/improve_silhouettes.py --upload <id> <id> ...   # promote
"""
import io
import os
import sys
import time
import json
from pathlib import Path

import httpx
import numpy as np
from dotenv import load_dotenv
from PIL import Image
from scipy import ndimage
from rembg import remove, new_session

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

SB_URL = os.environ["SUPABASE_URL"]
SECRET = os.environ["SUPABASE_JWT_SECRET"]
UA = {"User-Agent": "SilhouetteleBot/1.0 (contact@silhouettele.cc)"}
REVIEW = BACKEND / "scripts" / "review"
REVIEW.mkdir(exist_ok=True)
_SESSION = new_session("u2net")

# WEAK buildings -> Commons search query
WEAK = {
    "b071": "Brooklyn Bridge", "b072": "Edinburgh Castle", "b074": "Mont Saint-Michel",
    "b075": "Charminar Hyderabad", "b081": "Macau Tower", "b085": "Westminster Abbey",
    "b086": "St Paul's Cathedral London", "b087": "Sacre-Coeur Paris", "b088": "Saint Isaac's Cathedral",
    "b094": "Potala Palace", "b095": "Osaka Castle", "b096": "Matsumoto Castle",
    "b097": "Prague Castle", "b098": "Buckingham Palace", "b099": "Bran Castle",
    "b100": "Chateau de Chambord", "b102": "Ponte Vecchio Florence", "b103": "Rialto Bridge Venice",
    "b110": "Abu Simbel", "b117": "Capital Gate Abu Dhabi", "b120": "Sapporo TV Tower",
}


def commons_candidates(query, n=6):
    r = httpx.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": n,
        "prop": "imageinfo", "iiprop": "url|mime|size", "iiurlwidth": 1200,
    }, headers=UA, timeout=30)
    out = []
    pages = r.json().get("query", {}).get("pages", {})
    for p in pages.values():
        ii = p.get("imageinfo", [{}])[0]
        url = ii.get("thumburl") or ii.get("url")
        mime = ii.get("mime", "")
        if url and mime.startswith("image") and "svg" not in mime:
            out.append(url)
    return out


def to_silhouette(img_bytes):
    cut = remove(img_bytes, session=_SESSION)
    img = Image.open(io.BytesIO(cut)).convert("RGBA")
    alpha = img.split()[3]
    mask = alpha.point(lambda a: 255 if a > 110 else 0).convert("L")
    bbox = mask.getbbox()
    if not bbox:
        return None, -1
    mask = mask.crop(bbox)
    arr = np.array(mask) > 127
    total = int(arr.sum())
    if total < 500:
        return None, -1
    lbl, ncomp = ndimage.label(arr)
    sizes = ndimage.sum(arr, lbl, range(1, ncomp + 1))
    largest = sizes.max() / total            # 1.0 = single clean object
    h, w = arr.shape
    bottom = arr[int(h * 0.93):, :].mean()    # filled base => likely ground clutter
    aspect = h / w
    # cleanliness score
    score = largest - 0.35 * max(0, bottom - 0.7) - 0.15 * max(0, ncomp - 1) / 10
    w0, h0 = mask.size
    sil = Image.new("RGB", (w0, h0), (255, 255, 255))
    sil.paste(Image.new("RGB", (w0, h0), (0, 0, 0)), (0, 0), mask)
    side = int(max(w0, h0) * 1.18)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(sil, ((side - w0) // 2, (side - h0) // 2))
    canvas = canvas.resize((1024, 1024))
    return canvas, round(float(score), 3)


def build():
    chosen = {}
    for bid, query in WEAK.items():
        try:
            urls = commons_candidates(query)
            best = None
            for u in urls[:6]:
                try:
                    raw = httpx.get(u, timeout=40, headers=UA, follow_redirects=True).content
                    sil, score = to_silhouette(raw)
                    if sil is None:
                        continue
                    if best is None or score > best[1]:
                        best = (sil, score, u)
                except Exception:
                    continue
            if best:
                best[0].save(REVIEW / f"{bid}.png")
                chosen[bid] = {"score": best[1], "url": best[2]}
                print(f"{bid} {query}: best score={best[1]} <- {best[2][:80]}", flush=True)
            else:
                print(f"{bid} {query}: NO CANDIDATE", flush=True)
        except Exception as e:
            print(f"{bid} {query}: ERROR {e}", flush=True)
    (REVIEW / "chosen.json").write_text(json.dumps(chosen, indent=2))
    print(f"\nSaved {len(chosen)} candidates to {REVIEW}")


def upload(ids):
    for bid in ids:
        path = REVIEW / f"{bid}.png"
        if not path.exists():
            print(f"{bid}: no review file")
            continue
        r = httpx.post(
            f"{SB_URL}/storage/v1/object/silhouettes/{bid}.png",
            content=path.read_bytes(),
            headers={"apikey": SECRET, "Authorization": f"Bearer {SECRET}",
                     "Content-Type": "image/png", "x-upsert": "true"},
            timeout=60)
        print(f"{bid}: upload {r.status_code}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--upload":
        upload(sys.argv[2:])
    else:
        build()
