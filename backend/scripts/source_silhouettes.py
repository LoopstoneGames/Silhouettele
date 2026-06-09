"""Source real landmark photos from Wikipedia, background-remove with rembg,
convert to clean black-on-white silhouettes, and upload to Supabase Storage.

No LLM key required.
"""
import io
import os
import sys
import time
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image
from rembg import remove, new_session

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")

SB_URL = os.environ["SUPABASE_URL"]
SECRET = os.environ["SUPABASE_JWT_SECRET"]
UA = {"User-Agent": "SilhouetteleBot/1.0 (contact@silhouettele.cc)"}

OUT = BACKEND / "scripts" / "sourced"
OUT.mkdir(exist_ok=True)
LOG = BACKEND / "scripts" / "source_log.txt"
_SESSION = new_session("u2net")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def wiki_image_url(title):
    t = urllib.parse.quote(title.replace(" ", "_"))
    r = httpx.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{t}",
        timeout=25, headers=UA, follow_redirects=True,
    )
    if r.status_code != 200:
        return None
    d = r.json()
    return (d.get("originalimage", {}).get("source")
            or d.get("thumbnail", {}).get("source"))


def to_silhouette(img_bytes):
    cut = remove(img_bytes, session=_SESSION)  # PNG bytes w/ alpha
    img = Image.open(io.BytesIO(cut)).convert("RGBA")
    alpha = img.split()[3]
    mask = alpha.point(lambda a: 255 if a > 110 else 0).convert("L")
    bbox = mask.getbbox()
    if not bbox:
        return None, 0.0
    mask = mask.crop(bbox)
    w, h = mask.size
    sil = Image.new("RGB", (w, h), (255, 255, 255))
    sil.paste(Image.new("RGB", (w, h), (0, 0, 0)), (0, 0), mask)
    side = int(max(w, h) * 1.18)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(sil, ((side - w) // 2, (side - h) // 2))
    canvas = canvas.resize((1024, 1024))
    # fill fraction = how much of the source bbox is foreground (sanity metric)
    fg = sum(1 for p in mask.getdata() if p > 127)
    fill = fg / (w * h)
    return canvas, round(fill, 3)


def upload(building_id, png_bytes):
    r = httpx.post(
        f"{SB_URL}/storage/v1/object/silhouettes/{building_id}.png",
        content=png_bytes,
        headers={"apikey": SECRET, "Authorization": f"Bearer {SECRET}",
                 "Content-Type": "image/png", "x-upsert": "true"},
        timeout=60,
    )
    return r.status_code, r.text[:160]


def process(items, do_upload=True):
    ok, fail = [], []
    for it in items:
        bid, name, title = it["building_id"], it["name"], it.get("wiki", it["name"])
        try:
            url = wiki_image_url(title)
            if not url:
                log(f"{bid} {name}: NO WIKI IMAGE (title='{title}')")
                fail.append(bid)
                continue
            raw = httpx.get(url, timeout=40, headers=UA, follow_redirects=True).content
            sil, fill = to_silhouette(raw)
            if sil is None:
                log(f"{bid} {name}: empty mask")
                fail.append(bid)
                continue
            buf = io.BytesIO()
            sil.save(buf, format="PNG")
            png = buf.getvalue()
            (OUT / f"{bid}.png").write_bytes(png)
            if do_upload:
                code, txt = upload(bid, png)
                if code in (200, 201):
                    log(f"{bid} {name}: OK (fill={fill}) uploaded")
                    ok.append(bid)
                else:
                    log(f"{bid} {name}: upload FAILED {code} {txt}")
                    fail.append(bid)
            else:
                log(f"{bid} {name}: OK (fill={fill}) [no upload]")
                ok.append(bid)
        except Exception as e:
            log(f"{bid} {name}: ERROR {e}")
            fail.append(bid)
    log(f"=== done: {len(ok)} ok, {len(fail)} failed. failed={fail} ===")
    return ok, fail


PILOT = [
    {"building_id": "b071", "name": "Brooklyn Bridge", "wiki": "Brooklyn Bridge"},
    {"building_id": "b072", "name": "Edinburgh Castle", "wiki": "Edinburgh Castle"},
    {"building_id": "b073", "name": "Berlin TV Tower", "wiki": "Fernsehturm Berlin"},
    {"building_id": "b074", "name": "Mont-Saint-Michel", "wiki": "Mont-Saint-Michel"},
    {"building_id": "b075", "name": "Charminar", "wiki": "Charminar"},
]

if __name__ == "__main__":
    from data.sourced_buildings import NEW_SOURCED
    ids = sys.argv[1:]
    batch = NEW_SOURCED if not ids else [b for b in NEW_SOURCED if b["building_id"] in ids]
    process(batch)
