# VVF 9.1 vCenter security-patch post — image mapping

Reality per the captures: vCenter **9.1.0.0000 → 9.1.0.0200** (critical SECURITY
patch), driven from vSphere Client → Updates → vCenter Server → Upgrade, reduced-
downtime switchover. Environment = `dc1-vcf-vc01.e360demo.com`.

Your `upgrade_N` files are **not** chronological. These are the ones referenced in
the post — confirm each matches before publishing (the rest are extras / ESXi-vLCM
/ VCF-installer shots that are out of scope for this vCenter-only post).

| Referenced in post | File | Should show |
|---|---|---|
| Pre-flight | `upgrade_1.jpg` | Summary BEFORE — 9.1.0.0000, "security update available" banner |
| Pre-flight | `DNS.jpg` | DNS resolution check |
| Step 1 | `upgrade_23.jpg` | Target version, "Upgrade with online depot" full frame |
| Step 2 | `upgrade_30.jpg` | "Select the available update" — 9.1.0.0200, PATCH, SECURITY |
| Step 2 | `upgrade_28.jpg` | Current 9.1.0.0000 → target 9.1.0.0200, UPDATE PLUGIN prompt |
| Step 3 | `upgrade_25.jpg` | Running readiness pre-checks |
| Step 4 | `upgrade_27.jpg` | vCenter Backup acknowledgment gate |
| Step 5 | `upgrade_16.jpg` | Deployment Type = Same Configuration |
| Step 5 | `upgrade_12.jpg` | Network Settings (temporary appliance IP) |
| Step 5 | `upgrade_11.jpg` | Target VM deployment — Review |
| Step 6 | `upgrade_6.jpg` | Prepare Upgrade / Switchover options |
| Step 6 | `upgrade_8.jpg` | Configure Switchover dialog |
| Step 7 | `upgrade_5.jpg` | Switchover in progress |
| Step 8 | `upgrade_4.jpg` | Switchover Completed (end screen) |
| Step 8 | `upgrade_2.jpg` | Summary AFTER — 9.1.0.0200, banner cleared |

Redact host FQDNs, `e360demo.com`, the vCenter + temporary IPs, the depot
hostname/creds, and accounts before these go public. **Do not publish** the VCF
Installer "Review Passwords" screen. See the DRAFT NOTES block in the post.
