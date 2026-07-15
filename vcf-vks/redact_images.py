#!/usr/bin/env python3
"""OCR-based redaction for the VKS/DOOM post screenshots.

Detects and blacks out, per image:
  - 10.103.50.x  (Supervisor addr 10.103.50.5, LoadBalancer 10.103.50.9, any VIP)
  - <host>.humbledgeeks.com  (host FQDNs)
  - <user>@humbledgeeks.com  (admin UPN admin.allen@humbledgeeks.com)

Operates only on the images the post actually references. Originals are backed up to
vks-images/_orig_backup/ first. Re-OCRs after redaction to verify nothing slipped through.
"""
import re, shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw
import pytesseract
from pytesseract import Output

MD = Path("vcf-vks/vcf-vks-kubernetes-doom.md")
IMG_ROOT = Path("vcf-vks")
BACKUP = Path("vcf-vks/vks-images/_orig_backup")
PAD = 4

PATTERNS = [
    re.compile(r'10\.103\.50\.\d{1,3}'),
    re.compile(r'[A-Za-z0-9_-]+\.humbledgeeks\.com'),
    re.compile(r'[A-Za-z0-9._-]+@humbledgeeks\.com'),
]

def matches(text):
    return any(p.search(text) for p in PATTERNS)

def line_groups(data):
    """Group OCR words into lines: key=(block,par,line) -> list of (text,l,t,w,h,idx)."""
    groups = {}
    for i, txt in enumerate(data['text']):
        if not txt or not txt.strip():
            continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        groups.setdefault(key, []).append(
            (txt, data['left'][i], data['top'][i], data['width'][i], data['height'][i]))
    return groups

WORD_HINT = re.compile(r'humbledgeeks|10\.103\.50|@humbledgeeks', re.I)

def _union(hit):
    return (min(s[2] for s in hit) - PAD, min(s[3] for s in hit) - PAD,
            max(s[2] + s[4] for s in hit) + PAD, max(s[3] + s[5] for s in hit) + PAD)

def detect_boxes(im):
    """Scan multiple OCR page-seg modes; match spaced AND de-spaced lines; plus a
    word-level backstop. Union every hit so split/mis-segmented tokens still get covered."""
    boxes, found = [], []
    for psm in (3, 6, 11):
        data = pytesseract.image_to_data(im, output_type=Output.DICT, config=f'--psm {psm}')
        for words in line_groups(data).values():
            spaced, sp_sp = "", []
            despaced, sp_dp = "", []
            for (txt, l, t, w, h) in words:
                a = len(spaced); spaced += txt; sp_sp.append((a, len(spaced), l, t, w, h)); spaced += " "
                b = len(despaced); despaced += txt; sp_dp.append((b, len(despaced), l, t, w, h))
            for text, spans in ((spaced, sp_sp), (despaced, sp_dp)):
                for p in PATTERNS:
                    for m in p.finditer(text):
                        s, e = m.span()
                        hit = [x for x in spans if x[0] < e and x[1] > s]
                        if hit:
                            boxes.append(_union(hit)); found.append(m.group(0))
            for (txt, l, t, w, h) in words:           # word-level backstop
                if WORD_HINT.search(txt):
                    boxes.append((l - PAD, t - PAD, l + w + PAD, t + h + PAD)); found.append(txt)
    return boxes, found

def redact_image(path):
    im = Image.open(path).convert("RGB")
    boxes, found = detect_boxes(im)
    if boxes:
        draw = ImageDraw.Draw(im)
        for b in boxes:
            draw.rectangle(b, fill=(0, 0, 0))
        im.save(path, quality=92)
    return sorted(set(found))

def verify(path):
    im = Image.open(path).convert("RGB")
    leftover = []
    for psm in (3, 6, 11):
        txt = pytesseract.image_to_string(im, config=f'--psm {psm}')
        for p in PATTERNS:
            leftover += p.findall(txt)
    return sorted(set(leftover))

def main():
    refs = sorted(set(re.findall(r'\(vks-images/[^)]+\)', MD.read_text())))
    refs = [r[1:-1] for r in refs]  # strip ()
    BACKUP.mkdir(parents=True, exist_ok=True)
    total_boxes = 0
    report = []
    for rel in refs:
        src = IMG_ROOT / rel
        bak = BACKUP / Path(rel).name
        if not bak.exists():
            shutil.copy2(src, bak)            # back up original once
        else:
            shutil.copy2(bak, src)            # restore from backup so re-runs are idempotent
        boxes = redact_image(src)
        total_boxes += len(boxes)
        leftover = verify(src) if boxes else verify(src)
        status = "OK" if not leftover else "LEFTOVER!"
        if boxes or leftover:
            report.append((Path(rel).name, len(boxes), sorted(set(boxes)), leftover, status))
    print(f"Processed {len(refs)} images. Redaction boxes drawn: {total_boxes}\n")
    print(f"{'image':38} {'boxes':5} status")
    for name, n, found, leftover, status in report:
        print(f"{name:38} {n:<5} {status}")
        if found:
            print(f"    redacted: {found}")
        if leftover:
            print(f"    ⚠ STILL DETECTED: {leftover}")
    clean = [r for r in report if r[4] == "OK"]
    flagged = [r for r in report if r[4] != "OK"]
    print(f"\nImages with redactions: {len(report)} | verified clean: {len(clean)} | NEED REVIEW: {len(flagged)}")
    if flagged:
        print("⚠ Review these manually:", [r[0] for r in flagged])

if __name__ == "__main__":
    main()
