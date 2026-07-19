# IMAGE MANIFEST: VCF 9.1 Lifecycle & Upgrades

56 raw screenshots landed in `images/_inbox/` (upgrade_1 .. upgrade_56). This file
records what each one is, where it went, and every sensitive value found in it.
16 were selected and copied into the numbered section folders. The rest stay in
`_inbox/` unused, for the reasons listed below.

Environment in the captures: the dc3 / `hg-vcf-flexpod` VCF instance on
`*.humbledgeeks.com`. This is a real VCF management-components (fleet lifecycle)
upgrade, builds moving from 9.1.0.0100 to the 9.1.0.0400 line.

---

## READ THIS FIRST: security must-fix

**upgrade_24.jpg contains a cleartext password. Do not publish it, remove it from
the repo, and rotate that credential.**

- `upgrade_24.jpg` is the VCF Installer "Review Passwords" screen with the
  **VCF Operations admin password shown in cleartext** (value REDACTED from this file on
  2026-07-19 — it is a public repo; read it off the quarantined image if you need it),
  plus installer IP `10.103.16.19` and a full set of dc3 FQDNs and usernames. It is
  NOT used in the post. Because it is now sitting in `_inbox/` inside a git repo, the
  password should be treated as exposed: change it, and delete this file (or move it
  out of the repo). I can quarantine it into a `_SENSITIVE-DO-NOT-COMMIT/` folder if
  you want, just say so.
- `upgrade_29.jpg` is the same installer "Review Passwords" screen but passwords are
  **masked**. Out of scope, not used. Still shows dc3 FQDNs and usernames.

## FINAL DECISION 2026-07-19 — lab identifiers ARE published

Allen's call, and this **supersedes** the full-redaction pass described further down.
The post publishes the lab as-is, matching the VVF vCenter post's approach.

- **VISIBLE (not redacted):** `dc3-*.humbledgeeks.com` FQDNs, bare `dc3-*` short names
  and VM names, `hg-vcf-flexpod`, all `10.103.x` addressing, and the service accounts
  `administrator@vsphere.local` / `admin@vsp.local` / `admin@local`, plus task GUIDs.
- **STILL REDACTED, the only thing:** Allen's personal UPN
  **`admin.allen@humbledgeeks.com`** (upgrade_21 Tasks views).
- Implemented in `redact_images.py`: the pattern list is reduced to the UPN, and the
  former `MANUAL_BOXES` / `KEEP_REGIONS` / `APPROVED_LEFTOVER` entries are commented out
  rather than deleted, so the full pass can be restored by uncommenting.
- `images/_orig_backup/` holds the untouched originals. The script restores from backup
  before redacting, so it is safe to re-run after any policy change.
- **upgrade_24.jpg moved** to `_SENSITIVE-DO-NOT-COMMIT/` (gitignored). The exposed VCF
  Operations admin password **still needs rotating** — unaffected by this decision.

### Superseded: the earlier full-redaction pass

Kept because the findings still matter if the policy is ever reversed. That pass
redacted all FQDNs, shortnames, `10.x` IPs, service accounts and task GUIDs, left
`hg-vcf-flexpod` visible, and carved out two author-approved exposures (`upgrade_51`
chart labels, `upgrade_30` User Name rows 7-8).

### Verification note, worth remembering

OCR self-verification was **not** trustworthy here and reported "17/17 clean" three
separate times while real leaks were on screen. A visual review caught what OCR could
not, in three distinct failure modes:

1. `10.103.16.44` in upgrade_26 sat under the mouse cursor, so the redactor and the
   verifier misread the digits *identically* and agreed with each other.
2. `dc3-fleetlcm.humbledgeeks.com` in upgrade_47/48 reads perfectly from a narrow crop
   but returns nothing from the full image at any page-seg mode, contrast variant, or
   full-width strip. Both are pinned in `MANUAL_BOXES`.
3. Greedy de-spaced matching over-redacted whole rows (the Component column in
   upgrade_45/6, "Control Plane" in upgrade_26), which OCR obviously never flags.

**Always eyeball the images before publishing. Do not trust the "verified clean" line.**

---

## Redaction decision for the SHOTS ACTUALLY USED

Every placed screenshot carries lab identifiers. None of the 16 used shots exposes a
cleartext password (verified). Before you push to WordPress, decide keep-vs-redact to
match your prior posts. In the VKS/DOOM post you redacted dc3 FQDNs, the
`admin.allen@humbledgeeks.com` UPN, and 10.103.x addresses; in the VVF post you kept
lab names visible. Your call, but here is what is on screen in the used shots:

- **FQDNs** (all used shots): `dc3-ops01`, `dc3-vsp01`, `dc3-fleetlcm`, `dc3-vidb`,
  `dc3-shared01`, `dc3-auto-vip`, `dc3-sddcm`, `dc3-collector`, `dc3-vc01`,
  `dc3-auto-platform`, all `.humbledgeeks.com`.
- **IPs** (upgrade_26, upgrade_45, and others): `10.103.16.x` management range,
  DNS/NTP `10.103.20.11` / `10.103.20.12`, VCF services runtime pool
  `10.103.16.81-93`.
- **Usernames / UPNs**: `admin.allen@humbledgeeks.com` (upgrade_21 Tasks views),
  `administrator@vsphere.local` (upgrade_1, upgrade_51), `admin@vsp.local`.
- **Software depot ID**: visible in `upgrade_46` (NOT used); the **redacted** copy
  `upgrade_47` is the one placed in the post.
- **Task IDs**: present in several Tasks-tab shots (upgrade_21 etc). Low risk, your
  call.

---

## Placed images (used in the post, in order per section)

### images/01-old-way/  (Section: Where we came from)
| Order | File | Screen | Caption (in draft) |
|---|---|---|---|
| 1 | upgrade_51.jpg | SDDC Manager dashboard | single-instance console, workload domains + upgrades separate from Aria |
| 2 | upgrade_1.jpg | SDDC Manager Binary Management | where I pulled core bundles before VCF Operations |
| 3 | upgrade_50.jpg | SDDC Manager Lifecycle Management, deprecation banner | referenced at the "SDDC Manager UI is deprecated" line in the architecture section |

### images/02-architecture/  (Sections: What changed + Fleet vs Instance)
| Order | File | Screen | Caption (in draft) |
|---|---|---|---|
| 1 | upgrade_45.jpg | VCF Management Components tab, full service list | the whole architecture in one screen |
| 2 | upgrade_26.jpg | Component detail, fleet vs instance FQDNs | the split that decides shared vs per-instance |
| 3 | upgrade_30.jpg | Fleet Management tree | VCF Management + instances + standalone vCenters as one fleet |

### images/03-management-upgrade/  (Section: Upgrading the management components)
| Order | File | Screen | Caption (in draft) |
|---|---|---|---|
| 1 | upgrade_42.jpg | Set Target Version dialog | pick the fleet target build |
| 2 | upgrade_19.jpg | Component table, all Ready for upgrade | current-to-target paths resolved |
| 3 | upgrade_13.jpg | All nine selected, Run Prechecks (9) | precheck/upgrade the whole set |
| 4 | upgrade_14.jpg | Upgrade All Components confirmation modal | the commit point |
| 5 | upgrade_21.jpg | Tasks tab, workflow subtasks | set context, stage, precheck, prepare, upgrade, sync |
| 6 | upgrade_6.jpg | Components tab after upgrade | confirm what actually landed |

### images/04-core-upgrade/  (Section: Upgrading the core components)
| Order | File | Screen | Caption (in draft) |
|---|---|---|---|
| 1 | upgrade_32.jpg | dc3-wld01 Upgrades tab, Precheck Details | instance side, starts after fleet is current |

**Gap:** this section has only the precheck shot. No Plan Component Upgrade wizard,
Select Components / Target Version, Submit Plan, Upgrade Sequence card, or
Schedule / Start Now captures exist. Grab those on your next core upgrade.

### images/05-depot-binaries/  (Section: Binary and depot management)
| Order | File | Screen | Caption (in draft) |
|---|---|---|---|
| 1 | upgrade_48.jpg | Software Depot connection mode | Connected / Offline Depot / Disconnected |
| 2 | upgrade_47.jpg | Register step (redacted copy) | activation code, depot ID redacted |
| 3 | upgrade_49.jpg | Software Depot overview + storage | where downloaded bundles live |
| 4 | upgrade_56.jpg | VCF Installer Download Binaries | bundles downloaded before deploy/upgrade |

---

## Not used (still in images/_inbox/)

| File | Why not used |
|---|---|
| upgrade_2 | SDDC Manager Binary Management mid-sync; upgrade_1 already covers the old-tool binary view |
| upgrade_3, upgrade_4 | External SFTP backup config; out of scope (no backup image slot in this post) |
| upgrade_5, upgrade_7, upgrade_11, upgrade_35 | More management-upgrade in-progress states; redundant with the 6 chosen |
| upgrade_8 | Second copy of the component list; upgrade_45 chosen instead |
| upgrade_9, upgrade_10 | VCF Operations appliance self-update / System Status; nice but not needed for the flow |
| upgrade_12, upgrade_16, upgrade_23, upgrade_31, upgrade_33, upgrade_34, upgrade_36, upgrade_37, upgrade_38, upgrade_39, upgrade_40, upgrade_41, upgrade_43, upgrade_44 | Additional Tasks-tab / Upgrade-tab states; duplicates of the chosen sequence |
| upgrade_15, upgrade_17, upgrade_19(dup states), upgrade_20, upgrade_22 | Ready / in-progress / error refresh states; upgrade_20 shows a transient "Unable to retrieve fleet lifecycle component details" error (candidate for the follow-up known-issue post) |
| upgrade_18 | HPE Alletra / NimbleOS storage array UI; unrelated to VCF lifecycle |
| upgrade_24 | **CLEARTEXT PASSWORD. Do not publish. Remove from repo, rotate credential.** |
| upgrade_25 | Components tab with node IPs; upgrade_45/26 chosen instead |
| upgrade_27, upgrade_28 | Fleet Management > Passwords views; out of scope |
| upgrade_29 | Installer Review Passwords (masked); out of scope |
| upgrade_46 | Register step with depot ID visible; redacted copy upgrade_47 used instead |
| upgrade_52, upgrade_53, upgrade_54, upgrade_55 | Login pages; out of scope |

---

## Notes on sequencing

The management-upgrade set (Section 4 of the post) is the strongest and best
documented. Six shots carry the reader from setting the target version through the
confirm dialog, the running subtasks, and the after-state. If you want it tighter,
drop upgrade_13 or upgrade_21; if you want it fuller, upgrade_9/upgrade_10 (the
VCF Operations appliance upgrading itself) are good adds from `_inbox/`.
