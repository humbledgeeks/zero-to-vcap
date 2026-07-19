#!/usr/bin/env python3
"""Redact the three VKS/DOOM screenshots that the original redaction pass missed.

Found by a 2026-07-19 audit of the published images. Why the first pass missed them:

  * vks-55 / vks-56: the Windows dialogs render the address as "10. 103. 50. 9:5900",
    so tesseract emits it as separate tokens ("10.", "103.", "50.", "9:5900") and the
    r'10\\.103\\.50\\.\\d+' pattern never matches any single token. Full-image OCR on a
    2560px screenshot also skips the dialog entirely. Boxes here are therefore explicit
    coordinates measured from 3x-upscaled crops, not pattern hits.
  * vks-34: never processed at all. It is not referenced in the post markdown and was
    never uploaded to WordPress, so the original run (which iterates over the markdown's
    image refs) never saw it. Repo-only exposure, still worth fixing.

Originals are backed up to vks-images/_leftover_orig_backup/ before the first write, and
restored-then-redacted on re-runs, so this is idempotent.

Usage:  python vcf-vks/redact_leftovers.py [--verify-only]
"""
import shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw
import pytesseract

IMG = Path("vcf-vks/vks-images")
BACKUP = IMG / "_leftover_orig_backup"
VERIFY_ONLY = "--verify-only" in sys.argv

# (file, [boxes]) in ORIGINAL pixel coordinates, padded slightly beyond the measured bbox
TARGETS = {
    # Left edges start just inside the input field, not at the OCR bbox: the measured
    # bbox swept in the trailing "st:" / "to:" of the field LABEL, and blacking out part
    # of "Remote Host:" / "Connected to:" looks like a mistake rather than a redaction.
    "vks-55-tightvnc-connect.jpg": [(905, 395, 1100, 446)],   # Remote Host: 10.103.50.9:5900
    "vks-56-vnc-auth.jpg":         [(888, 388, 1080, 436)],   # Connected to: 10.103.50.9:5900
    "vks-34-discover-classes.jpg": [(1276, 187, 1825, 224)],  # sso:admin.allen@humbledgeeks.com
}

# What must NOT be readable afterwards. Spacing-tolerant, because the dialogs render the
# address with spaces after each dot and that is exactly what defeated the first pass.
import re
CHECKS = [
    re.compile(r'10\.?\s*103\.?\s*50\.?\s*\d{1,3}'),
    re.compile(r'admin[._]\s*allen\s*@\s*humbledgeeks\.com'),
]


def read_all(path):
    """OCR the image several ways and return one concatenated, de-spaced string."""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    out = []
    for psm in (3, 6, 11):
        out.append(pytesseract.image_to_string(im, config=f"--psm {psm}"))
        for top in range(0, H, max(H // 8, 1)):
            bot = min(top + H // 4, H)
            if bot - top < 20:
                continue
            crop = im.crop((0, top, W, bot))
            out.append(pytesseract.image_to_string(crop, config=f"--psm {psm}"))
            up = crop.resize((crop.width * 2, crop.height * 2))   # 2x catches small dialog text
            out.append(pytesseract.image_to_string(up, config=f"--psm {psm}"))
    return "".join(out)


def verify(path):
    txt = read_all(path)
    flat = re.sub(r'\s+', '', txt)
    hits = []
    for p in CHECKS:
        hits += p.findall(txt) + p.findall(flat)
    return sorted(set(hits))


failures = []
for name, boxes in TARGETS.items():
    src = IMG / name
    if not src.exists():
        print(f"[warn] missing: {name}")
        continue
    if not VERIFY_ONLY:
        BACKUP.mkdir(parents=True, exist_ok=True)
        bak = BACKUP / name
        if not bak.exists():
            shutil.copy2(src, bak)
        else:
            shutil.copy2(bak, src)          # restore first so re-runs are idempotent
        im = Image.open(src).convert("RGB")
        draw = ImageDraw.Draw(im)
        for b in boxes:
            draw.rectangle(b, fill=(0, 0, 0))
        im.save(src, quality=92)
    left = verify(src)
    status = "OK" if not left else "STILL LEAKING"
    print(f"{name:32} {status}")
    if left:
        print(f"    !! {left}")
        failures.append(name)

print(f"\n{len(TARGETS) - len(failures)}/{len(TARGETS)} clean")
if failures:
    print("NEEDS MANUAL REVIEW:", failures)
    sys.exit(1)
