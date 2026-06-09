"""Audit silhouette images: download, analyze 'silhouette-ness', build a montage.

A clean silhouette = mostly white/transparent background + a solid dark shape,
with very little mid-tone or colored area.
"""
import sys
import io
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

SB = "https://urpkmgxvshdlkiaucykf.supabase.co/storage/v1/object/public/silhouettes"


def fetch(bid):
    r = httpx.get(f"{SB}/{bid}.png", timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def analyze(img):
    small = img.resize((128, 128))
    px = list(small.getdata())
    n = len(px)
    white = black = colored = 0
    for r, g, b in px:
        mx, mn = max(r, g, b), min(r, g, b)
        sat = mx - mn
        if sat > 45:
            colored += 1
        elif mx > 215:
            white += 1
        elif mx < 70:
            black += 1
    midtone = n - white - black - colored
    def pct(x):
        return round(100 * x / n, 1)
    wp, bp, cp, mp = pct(white), pct(black), pct(colored), pct(midtone)
    # silhouette verdict
    verdict = "OK"
    if cp > 12:
        verdict = "NOT-SILHOUETTE (colored)"
    elif wp < 35:
        verdict = "NOT-SILHOUETTE (no light bg)"
    elif bp < 4:
        verdict = "WEAK (almost no dark shape)"
    elif mp > 35:
        verdict = "SOFT (lots of mid-tone)"
    else:
        verdict = "OK"
    return {"white%": wp, "black%": bp, "colored%": cp, "mid%": mp, "verdict": verdict}


def run(items, montage_name="montage.png", cols=5):
    results = []
    thumbs = []
    for bid, name in items:
        try:
            img = fetch(bid)
            a = analyze(img)
            results.append((bid, name, a))
            print(f"{bid} {name:30s} {a}")
            thumbs.append((bid, name, img))
        except Exception as e:
            print(f"{bid} {name}: ERROR {e}")
            results.append((bid, name, {"verdict": f"ERROR {e}"}))
    # build montage
    if thumbs:
        ts = 240
        pad = 26
        rows = (len(thumbs) + cols - 1) // cols
        W = cols * (ts + 10) + 10
        H = rows * (ts + pad + 10) + 10
        sheet = Image.new("RGB", (W, H), (240, 240, 240))
        d = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        except Exception:
            font = ImageFont.load_default()
        for i, (bid, name, img) in enumerate(thumbs):
            r, c = divmod(i, cols)
            x = 10 + c * (ts + 10)
            y = 10 + r * (ts + pad + 10)
            sheet.paste(img.resize((ts, ts)), (x, y))
            d.text((x + 2, y + ts + 4), f"{bid} {name[:24]}", fill=(0, 0, 0), font=font)
        out = BACKEND / "scripts" / montage_name
        sheet.save(out)
        print(f"\nMontage saved: {out}")
    return results


if __name__ == "__main__":
    from scripts.new_buildings import PILOT
    items = [(b["building_id"], b["name"]) for b in PILOT]
    run(items, "montage_pilot.png")
