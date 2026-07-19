#!/usr/bin/env python3
"""OCR-based redaction for the VCF 9.1 Lifecycle & Upgrades post screenshots.

Detects and blacks out, per image:
  - <host>.humbledgeeks.com     (dc3-ops01, dc3-sddcm, dc3-vc01, dc3-fleetlcm, ...)
  - <user>@humbledgeeks.com     (admin.allen@humbledgeeks.com)
  - administrator@vsphere.local / admin@vsp.local
  - 10.103.x.x                  (mgmt range, DNS/NTP, VCF services runtime pool)

Operates only on the images the post actually references (the 17 placed shots under
images/NN-folder/), NOT the raw _inbox/ dump. Originals are backed up to
images/_orig_backup/ first, and restored-then-redacted on re-runs so this is idempotent.
Re-OCRs after redaction to verify nothing slipped through.

Adapted from vcf-vks/redact_images.py. Differences: the markdown lives in draft/ and
references ../images/NN-folder/<name>.jpg, so refs resolve against the post root.

Usage:  python VCF-9.1-Lifecycle-Upgrades/redact_images.py
"""
import re, shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import pytesseract
from pytesseract import Output

ROOT = Path("VCF-9.1-Lifecycle-Upgrades")
MD = ROOT / "draft" / "zero-to-vcap-vcf91-lifecycle-upgrades.md"
BACKUP = ROOT / "images" / "_orig_backup"
PAD = 4

# NOTE on the digit classes below: OCR routinely misreads digits in screenshots as
# look-alike letters (1->I/l, 0->O/o, 5->S), especially where the mouse cursor overlaps
# the text. A strict \d IP pattern let 10.103.16.44 slip through upgrade_26 AND slip
# past the verify pass, because both sides made the same misread. Match the look-alikes.
D = r'[\dIiLlOoSs]'

# POLICY CHANGE 2026-07-19 (Allen's call, supersedes the original full-redaction pass):
# lab identifiers are fine to publish. FQDNs (dc3-*.humbledgeeks.com), bare dc3-* short
# names, hg-vcf-flexpod, 10.103.x addressing, service accounts (administrator@vsphere.local,
# admin@vsp.local, admin@local) and task GUIDs are all LEFT VISIBLE, matching the VVF post.
# The ONLY thing still redacted is Allen's personal UPN. The patterns for everything else
# are kept below, commented out, so the full pass can be restored by uncommenting.
PATTERNS = [
    re.compile(r'[A-Za-z0-9._-]+@humbledgeeks\.com'),   # personal UPN (admin.allen@...)
    # re.compile(r'[A-Za-z0-9_-]+\.humbledgeeks\.com'),
    # re.compile(r'[A-Za-z0-9._-]+@vsphere\.local'),
    # re.compile(r'[A-Za-z0-9._-]+@vsp\.local'),
    # re.compile(r'\b10[.,]' + D + r'{1,3}[.,]' + D + r'{1,3}[.,]' + D + r'{1,3}\b'),
    # re.compile(r'\bdc3-[A-Za-z0-9._-]+'),
    # re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'),
]

# word-level backstop for tokens OCR splits or mangles at line level
WORD_HINT = re.compile(r'@humbledgeeks|admin\.allen', re.I)


def line_groups(data):
    """Group OCR words into lines: key=(block,par,line) -> list of (text,l,t,w,h)."""
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


def _trim(hit):
    """Narrow a line-level match to the sensitive words, as SEPARATE runs.

    On the de-spaced pass the whole line is one string, so a pattern can greedily grab
    neighbouring columns ("Fleetlifecycledc3-fleetlcm.humbledgeeks.com" swallows the
    Component column; a Nodes row swallows "Control Plane" between the VM name and the
    IP). Returning one box from the first to the last sensitive word still erases the
    harmless column in the middle, so emit one box per contiguous run of sensitive words
    and leave the gaps alone.

    If no word looks sensitive on its own, the value is split across words we cannot
    identify individually, so fall back to covering the whole match.
    """
    runs, cur = [], []
    for w in hit:
        if WORD_HINT.search(w[6]):
            cur.append(w)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return runs if runs else [hit]


def variants(im):
    """The image as-is, plus a contrast-boosted copy.

    When a modal is open the VCF Operations UI dims the page behind it, leaving grey-on-
    grey text that tesseract reads as nothing at all. That is how a fully legible
    dc3-fleetlcm.humbledgeeks.com header survived both the redaction and the verify pass
    on upgrade_47/48. Autocontrast on the greyscale copy restores it. Same geometry, so
    boxes from either variant map onto the original unchanged.
    """
    return [im, ImageOps.autocontrast(im.convert("L")).convert("RGB")]


def _scan(img, psms, dx=0, dy=0):
    """OCR one image region and return (boxes, found), shifted by (dx, dy)."""
    boxes, found = [], []
    for psm in psms:
        data = pytesseract.image_to_data(img, output_type=Output.DICT, config=f'--psm {psm}')
        for words in line_groups(data).values():
            spaced, sp_sp = "", []
            despaced, sp_dp = "", []
            for (txt, l, t, w, h) in words:
                l, t = l + dx, t + dy          # region-local -> original coordinates
                a = len(spaced); spaced += txt; sp_sp.append((a, len(spaced), l, t, w, h, txt)); spaced += " "
                b = len(despaced); despaced += txt; sp_dp.append((b, len(despaced), l, t, w, h, txt))
            for text, spans in ((spaced, sp_sp), (despaced, sp_dp)):
                for p in PATTERNS:
                    for m in p.finditer(text):
                        s, e = m.span()
                        hit = [x for x in spans if x[0] < e and x[1] > s]
                        for run in _trim(hit):
                            if run:
                                boxes.append(_union(run)); found.append(m.group(0))
            for (txt, l, t, w, h) in words:           # word-level backstop
                if WORD_HINT.search(txt):
                    l, t = l + dx, t + dy
                    boxes.append((l - PAD, t - PAD, l + w + PAD, t + h + PAD)); found.append(txt)
    return boxes, found


def detect_boxes(im):
    """Scan each contrast variant whole, then again in overlapping horizontal strips.

    Tiling is not optional. On a full 3780px-wide screenshot tesseract simply skips
    regions: the "dc3-fleetlcm.humbledgeeks.com" header on upgrade_47/48 is read
    perfectly from a crop but returns nothing from the full image, at every page-seg
    mode. Strips overlap by half so text near a cut is still read intact somewhere.
    """
    boxes, found = [], []
    W, H = im.size
    for v in variants(im):
        b, f = _scan(v, (3, 6, 11))
        boxes += b; found += f
        strip = max(H // 6, 1)
        for top in range(0, H, strip // 2 or 1):
            bot = min(top + strip, H)
            if bot - top < 20:
                continue
            b, f = _scan(v.crop((0, top, W, bot)), (6, 11), dy=top)
            boxes += b; found += f
    return boxes, found


# Values OCR cannot read, so no pattern can ever catch them. Boxes are in ORIGINAL
# pixel coordinates, applied unconditionally on top of the detected boxes.
#   upgrade_26: the mouse cursor sits on top of the "Fleet components FQDN" IP
#   (10.103.16.44), so every page-seg mode misreads the digits and the verify pass
#   misreads them identically. Found by eye, not by OCR. Do not remove.
#   upgrade_47/48: the Software Depot header "dc3-fleetlcm.humbledgeeks.com" is read
#   perfectly from a narrow crop but returns NOTHING from the full image or from a
#   full-width strip, at every page-seg mode and both contrast variants. A visual review
#   caught it; OCR never will. Coordinates measured from a targeted crop of the original.
# All three entries covered an IP or an FQDN, which the 2026-07-19 policy change now
# publishes. Kept (commented) because the coordinates were expensive to find and OCR
# cannot rediscover them if the full-redaction pass is ever restored.
MANUAL_BOXES = {
    # "images/02-architecture/upgrade_26.jpg": [(2125, 1038, 2315, 1090)],   # 10.103.16.44 under the cursor
    # "images/05-depot-binaries/upgrade_47.jpg": [(1265, 124, 1900, 184)],   # dc3-fleetlcm header
    # "images/05-depot-binaries/upgrade_48.jpg": [(1258, 122, 1896, 184)],   # dc3-fleetlcm header
}


# Regions the author decided to leave readable, overriding the global patterns. These
# are deliberate, informed exceptions, not bugs — do not "fix" them by deleting entries.
#   upgrade_51: the Top Domains bar labels ("humbledgeeks", "dc3-wld01"). Boxing them
#     left three charts unlabeled and destroyed the point of the shot. Allen chose to
#     publish the domain names here. The administrator@vsphere.local in the top-right
#     header is OUTSIDE these regions and stays redacted.
#   upgrade_30: the User Name column rows 7-8 ("admin@vsp.local"). Rows 1-6 show
#     generic admin/root/vmware-system-user, so redacting only these two read as broken.
#     Allen chose to publish it. The Component IP/FQDN column stays redacted.
# Both carve-outs are now redundant: the values they protected (chart domain labels,
# admin@vsp.local) are published wholesale under the 2026-07-19 policy.
KEEP_REGIONS = {}


# Exact values the author approved for publication (see KEEP_REGIONS). Kept as an
# explicit allowlist so an unexpected leak in the same image still fails verification.
APPROVED_LEFTOVER = {}


def _keep(box, regions):
    """True if a detected box sits inside an author-approved keep-visible region."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in regions)


def redact_image(path, rel=None):
    im = Image.open(path).convert("RGB")
    boxes, found = detect_boxes(im)
    keep = KEEP_REGIONS.get(rel, [])
    if keep:
        boxes = [b for b in boxes if not _keep(b, keep)]
    for b in MANUAL_BOXES.get(rel, []):
        boxes.append(b); found.append(f"[manual box {b}]")
    if boxes:
        draw = ImageDraw.Draw(im)
        for b in boxes:
            draw.rectangle(b, fill=(0, 0, 0))
        im.save(path, quality=92)
    return sorted(set(found))


def verify(path):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    leftover = []
    # verify over the same variants AND the same strips as the redactor, otherwise the
    # check inherits the redactor's blind spots and cheerfully confirms its own misses
    regions = []
    for v in variants(im):
        regions.append(v)
        strip = max(H // 6, 1)
        for top in range(0, H, strip // 2 or 1):
            bot = min(top + strip, H)
            if bot - top >= 20:
                regions.append(v.crop((0, top, W, bot)))
    for reg in regions:
        for psm in (3, 6, 11):
            txt = pytesseract.image_to_string(reg, config=f'--psm {psm}')
            for p in PATTERNS:
                leftover += p.findall(txt)
    return sorted(set(leftover))


def main():
    # refs look like ](../images/NN-folder/upgrade_X.jpg) — resolve against the post root
    refs = sorted(set(re.findall(r'\]\(\.\./(images/[^)]+)\)', MD.read_text())))
    if not refs:
        sys.exit("[error] no ../images/ refs found in the draft")
    BACKUP.mkdir(parents=True, exist_ok=True)
    report = []
    for rel in refs:
        src = ROOT / rel
        if not src.exists():
            print(f"[warn] referenced but missing: {rel}")
            continue
        # back up under folder-qualified name (upgrade_1.jpg exists in more than one folder)
        bak = BACKUP / rel.replace("/", "__").replace("images__", "")
        if not bak.exists():
            shutil.copy2(src, bak)            # back up original once
        else:
            shutil.copy2(bak, src)            # restore first so re-runs are idempotent
        found = redact_image(src, rel)
        # Anything still readable inside a keep-visible region is an approved exposure,
        # not a miss. Subtract only those exact values so a genuinely new leak in the
        # same image still fails the check.
        approved = APPROVED_LEFTOVER.get(rel, set())
        leftover = [v for v in verify(src) if v not in approved]
        status = "OK" if not leftover else "LEFTOVER!"
        report.append((rel, len(found), found, leftover, status))

    print(f"Processed {len(report)} referenced images.\n")
    print(f"{'image':44} {'hits':5} status")
    for rel, n, found, leftover, status in report:
        print(f"{rel:44} {n:<5} {status}")
        if found:
            print(f"    redacted: {found}")
        if leftover:
            print(f"    !! STILL DETECTED: {leftover}")
    clean = [r for r in report if r[4] == "OK"]
    flagged = [r for r in report if r[4] != "OK"]
    print(f"\nverified clean: {len(clean)}/{len(report)} | NEED REVIEW: {len(flagged)}")
    if flagged:
        print("Review these manually:", [r[0] for r in flagged])
        sys.exit(1)


if __name__ == "__main__":
    main()
