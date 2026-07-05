#!/usr/bin/env python3
"""Targeted OCR redaction for the VLAN18 cross-vCenter vMotion post.

Scope (agreed): black out only the values that are NOT already shown in the
body prose, code blocks, or the two intro diagrams:
  - serverGuid / vCenter instance UUID (move-19 web-console URL bar)
  - SHA-256 certificate fingerprint (move-03) - long runs of hex pairs
  - admin usernames / UPN: *@humbledgeeks.com, Administrator@vsphere.local,
    bare "admin.allen"

Deliberately KEPT visible (they are in the body + diagrams): bare host FQDNs
like dc3-vc02.humbledgeeks.com, and the 10.103.x.x IPs.

Originals backed up to vlan-images/_redact_backup/ (distinct from the existing
_orig_backup). Idempotent: re-runs restore from backup first. Re-OCRs after to
verify. Optional MANUAL boxes cover anything OCR cannot read (URL bar / tiny
cert text), given in ORIGINAL-pixel coords.
"""
import re, shutil
from pathlib import Path
from PIL import Image, ImageDraw
import pytesseract
from pytesseract import Output

MD = Path("vcf-vlan-migration/vcf-vlan18-legacy-vlan-on-wld.md")
IMG_ROOT = Path("vcf-vlan-migration")
BACKUP = Path("vcf-vlan-migration/vlan-images/_redact_backup")
PAD = 4

PATTERNS = [
    re.compile(r'serverGuid\s*=?\s*[0-9a-fA-F-]{8,}'),
    re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I),
    # SHA-256 fingerprint: >=8 hex pairs in a row (MAC is only 6 -> safe)
    re.compile(r'(?:[0-9A-Fa-f]{2}[\s:]+){7,}[0-9A-Fa-f]{2}'),
    re.compile(r'[A-Za-z0-9._-]+@[A-Za-z0-9.-]*humbledgeeks\.com'),
    re.compile(r'Administrator@vsphere\.local', re.I),
    re.compile(r'admin[._ ]allen'),
]

# Dimmed-modal shots where OCR can't read the greyed top-right admin.allen UPN.
# Box is right-anchored and computed from image size (handles width variance).
VSPHERE_HEADER = {
    "move-02-source-vcenter-creds.jpg",
    "move-03-security-alert-cert.jpg",
    "move-04-source-vcenter-connected.jpg",
    "move-05-select-rhel9-poweredon.jpg",
    "move-06-compute-evc-error.jpg",
    "move-09-select-rhel9-poweredoff.jpg",
    "move-10-compute-compat-success.jpg",
    "move-11-storage-vmfs01.jpg",
    "move-12-select-folder.jpg",
    "move-13-select-network-picker.jpg",
    "move-14-network-mapping-kb56991.jpg",
    "move-15-ready-to-complete-finish.jpg",
}

def vsphere_header_box(im):
    W, H = im.size
    return (W - 745, 14, W - 290, 92)

# Manual fallback boxes in ORIGINAL pixel coords: {filename: [(x0,y0,x1,y1), ...]}
MANUAL = {
    "move-03-security-alert-cert.jpg": [
        (1415, 1382, 2360, 1498),   # SHA-256 fingerprint, both hex rows
    ],
    # NSX Host Switch modal, browser chrome (3840x2160): greyed top-right UPN
    "vlan-10-deadend2-hostswitch-overlay-only-edit.jpg": [(3225, 182, 3778, 250)],
    "vlan-12-deadend2-both-tz-mode-standard-apply-greyed.jpg": [(3225, 182, 3778, 250)],
    "vlan-16-deadend2-tz-dropdown-vlan-tz-highlighted.jpg": [(3225, 182, 3778, 250)],
    # NSX Host Switch read-only, no browser chrome (3790x1964): greyed top-right UPN
    "vlan-24-hostswitch-both-tz-mode-standard.jpg": [(3195, 98, 3742, 165)],
    # vCenter Edit Settings in-browser: URL-bar serverGuid + greyed UPN + task admin.allen
    "vlan-34-vm-nic-dropdown-seg-vlan18.jpg": [
        (1300, 3, 2125, 62),        # serverGuid in the browser URL bar
        (3030, 96, 3525, 165),      # greyed top-right admin.allen UPN
        (1775, 1872, 2140, 1918),   # HUMBLEDGEEKS.COM\admin.allen task initiator
    ],
}

WORD_HINT = re.compile(r'humbledgeeks|vsphere\.local|serverGuid', re.I)

def line_groups(data):
    groups = {}
    for i, txt in enumerate(data['text']):
        if not txt or not txt.strip():
            continue
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        groups.setdefault(key, []).append(
            (txt, data['left'][i], data['top'][i], data['width'][i], data['height'][i]))
    return groups

def _union(hit):
    return (min(s[2] for s in hit) - PAD, min(s[3] for s in hit) - PAD,
            max(s[2] + s[4] for s in hit) + PAD, max(s[3] + s[5] for s in hit) + PAD)

def detect_boxes(im):
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
            for (txt, l, t, w, h) in words:
                if WORD_HINT.search(txt) and '@' in txt:   # UPN word backstop
                    boxes.append((l - PAD, t - PAD, l + w + PAD, t + h + PAD)); found.append(txt)
    return boxes, found

def redact_image(path):
    im = Image.open(path).convert("RGB")
    boxes, found = detect_boxes(im)
    for b in MANUAL.get(path.name, []):
        boxes.append(b); found.append("MANUAL")
    if path.name in VSPHERE_HEADER:
        boxes.append(vsphere_header_box(im)); found.append("MANUAL-hdr")
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
    refs = sorted(set(re.findall(r'\(vlan-images/[^)]+\)', MD.read_text())))
    refs = [r[1:-1] for r in refs]
    BACKUP.mkdir(parents=True, exist_ok=True)
    total_boxes = 0
    report = []
    for rel in refs:
        src = IMG_ROOT / rel
        bak = BACKUP / Path(rel).name
        if not bak.exists():
            shutil.copy2(src, bak)
        else:
            shutil.copy2(bak, src)
        found = redact_image(src)
        total_boxes += len(found)
        leftover = verify(src)
        status = "OK" if not leftover else "LEFTOVER!"
        if found or leftover:
            report.append((Path(rel).name, found, leftover, status))
    print(f"Processed {len(refs)} images. Total redactions: {total_boxes}\n")
    for name, found, leftover, status in report:
        print(f"{name:40} {status}")
        if found:
            print(f"    redacted: {found}")
        if leftover:
            print(f"    STILL DETECTED: {leftover}")
    flagged = [r for r in report if r[3] != "OK"]
    print(f"\nImages touched: {len(report)} | NEED REVIEW: {len(flagged)}")
    if flagged:
        print("Review manually:", [r[0] for r in flagged])

if __name__ == "__main__":
    main()
