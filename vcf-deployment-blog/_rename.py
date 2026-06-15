#!/usr/bin/env python3
"""Stage 0 rename for the re-uploaded 71-image set.
New set is reverse-numbered: vcf_71 = deploy step 01 ... vcf_1 = step 71.
So old_N = 72 - seq. Renames in place and writes image-rename-map.csv.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

SLUGS = {
    1: "installer-landing",
    2: "depot-settings-overview",
    3: "broadcom-vcf-portal-home",
    4: "register-software-depot-start",
    5: "online-depot-activation-code",
    6: "register-software-depot-form",
    7: "depot-activation-code-generated",
    8: "online-depot-authenticate",
    9: "depot-connection-active",
    10: "binary-management-download-summary",
    11: "binary-management-component-list",
    12: "binary-management-select-all",
    13: "binary-download-in-progress",
    14: "binary-download-complete",
    15: "installer-binaries-downloaded",
    16: "deployment-wizard-dropdown",
    17: "deployment-wizard-introduction",
    18: "deployment-paths",
    19: "esxi-911-installer-welcome",
    20: "esxi-911-installation-complete",
    21: "plan-existing-component",
    22: "plan-size-options",
    23: "plan-network-options-default",
    24: "plan-network-options-custom",
    25: "plan-storage-vmfs-fc",
    26: "plan-review-prerequisites",
    27: "plan-review-prerequisites-fqdns",
    28: "plan-review-prerequisites-environment",
    29: "fqdns-ip-addresses-detail",
    30: "prefill-fqdns-pattern",
    31: "prefill-fqdns-generated",
    32: "prefill-fqdns-full-list",
    33: "prefill-fqdns-validate",
    34: "prefill-fqdns-all-validated",
    35: "prepare-general-information",
    36: "prepare-hosts-fingerprints",
    37: "esxi-hardening-script-start",
    38: "esxi-hardening-dns-host-discovery",
    39: "esxi-hardening-preflight-summary",
    40: "esxi-hardening-apply-compliance",
    41: "esxi-cert-regen-intro",
    42: "esxi-cert-regen-https-method",
    43: "esxi-cert-regen-run",
    44: "prepare-hosts-resource-warning",
    45: "prepare-hosts-capacity-breakdown",
    46: "plan-size-options-simple-small",
    47: "prepare-hosts-simple-capacity",
    48: "prepare-hosts-resource-warning-modal",
    49: "prepare-networks",
    50: "prepare-vcf-management",
    51: "prepare-vcenter",
    52: "prepare-storage-vmfs-fc",
    53: "prepare-dswitch-topology",
    54: "prepare-dswitch-vds01",
    55: "prepare-dswitch-vds02-nsx",
    56: "prepare-nsx-manager",
    57: "prepare-sddc-manager",
    58: "deploy-review-summary",
    59: "deploy-review-sections",
    60: "deploy-validation-start",
    61: "deploy-validation-progress",
    62: "deploy-validation-9of15",
    63: "deploy-validation-capacity-warning",
    64: "deploy-validation-complete",
    65: "deployment-in-progress-start",
    66: "deployment-in-progress-vcenter-done",
    67: "deployment-nsx-cluster-complete",
    68: "deployment-vcf-platform-progress",
    69: "deployment-operations-appliance",
    70: "deployment-management-services-complete",
    71: "deployment-complete-success",
}

assert len(SLUGS) == 71, len(SLUGS)

rows = []
# rename to temp first to avoid any edge collisions, then final
for seq in range(1, 72):
    old = HERE / f"vcf_{72 - seq}.jpg"
    new = HERE / f"vcf-9-1-deploy-{seq:02d}-{SLUGS[seq]}.jpg"
    if not old.exists():
        raise SystemExit(f"missing {old.name}")
    if new.exists():
        raise SystemExit(f"target exists {new.name}")
    old.rename(new)
    rows.append((f"vcf_{72 - seq}.jpg", new.name, seq, SLUGS[seq]))

with (HERE / "image-rename-map.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["original", "renamed", "deploy_seq", "slug"])
    w.writerows(rows)

print(f"Renamed {len(rows)} files. Leftover vcf_N:",
      len(list(HERE.glob("vcf_*.jpg"))))
