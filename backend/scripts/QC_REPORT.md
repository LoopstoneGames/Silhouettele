# Silhouette Dataset — QC Report (2026-06-06)

## Summary
Expanded the building set from **60 → 114** and quality-checked every silhouette.

| Source | Count | Notes |
|---|---|---|
| Original | 60 | b001–b060 (unchanged) |
| AI-generated pilot (kept) | 9 | b061–b068, b070 (b069 mosque removed) |
| Real-photo → rembg silhouettes | 45 | b071–b123 (after removing BAD + duplicates) |
| **Total live** | **114** | all images verified 200 OK in Supabase Storage |

## How the new silhouettes were made
Real landmark photos were pulled from Wikipedia, background-removed with `rembg`
(U²-Net), and rendered as solid black-on-white, centered 1024×1024 PNGs, then
uploaded to the `silhouettes` bucket. **No LLM / AI image generation** is used
(integration removed per request). Pipeline lives in `backend/scripts/source_silhouettes.py`
and auditing in `backend/scripts/audit_silhouettes.py`.

## Removed during QC
- **Mosque (b069 Sheikh Zayed)** — weak AI silhouette, removed per request.
- **Duplicates** — b118 Atomium (= b041), b119 Chrysler (= b038).
- **BAD cutouts (unrecognizable / abstract)** — removed:
  - b083 Shanghai Tower, b101 Charles Bridge, b104 Guggenheim Bilbao,
    b105 Walt Disney Concert Hall, b115 Lakhta Center, b116 MahaNakhon.
  - (Twisty glass towers and long bridges don't cut out into readable silhouettes.)

## Flagged WEAK (kept & playable, but base clutter / soft edges — optional to replace later)

**Update (2026-06-06):** 12 of the original WEAK silhouettes were upgraded to GOOD by
sourcing cleaner alternative photos from Wikimedia Commons (auto-scored by connected-
component cleanliness, then visually verified): b071 Brooklyn Bridge, b072 Edinburgh Castle,
b075 Charminar, b081 Macau Tower, b087 Sacré-Cœur, b088 Saint Isaac's, b095 Osaka Castle,
b096 Matsumoto Castle, b100 Château de Chambord, b110 Abu Simbel, b117 Capital Gate,
b120 Sapporo TV Tower.

**Remaining WEAK (9)** — correct landmark but cluttered/ambiguous; left as-is because the
alternative candidates weren't clearly better (or were wrong subjects):
b074 Mont-Saint-Michel, b085 Westminster Abbey, b086 St Paul's Cathedral, b094 Potala Palace,
b097 Prague Castle, b098 Buckingham Palace, b099 Bran Castle, b102 Ponte Vecchio, b103 Rialto Bridge.

Tooling: `backend/scripts/improve_silhouettes.py` (pulls Commons candidates → scores → saves
to a review folder; `--upload <id>...` promotes the approved ones).

## Note on daily puzzle selection
The daily puzzle is chosen deterministically from the building list by date. Because
the list size changed (→114), the building shown for a given date shifts — expected,
not a bug.
