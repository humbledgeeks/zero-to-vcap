# vcf-spine

NSX edge "spine" build for the VCF 9.1 management domain (dc3 lab) — the edge cluster + Tier-0 + external connection + VPC IP blocks that populate the **VPC connectivity profile** the vSphere Supervisor wizard needs. Part of the *Zero to VCAP* series.

## Status (2026-06-14)
**Wizard Step 2 (Edge Cluster) complete** — both edges (`dc3-nsx-edge01` + `dc3-nsx-edge02`) in the cluster, collapsed TEP on VLAN 32, Run Checks green. **Next:** Step 3 — Tier-0, VLAN 44 uplinks, VPC IP blocks. See `session-state.md` to resume.

## Files
| File | What it is |
|---|---|
| `runbook.md` | Master build runbook — all values, every wizard step, post-deploy, validation. The source of truth. |
| `session-state.md` | Resume handoff — exactly where the build is and the next action. |
| `meraki-underlay-as-built.md` | As-built record of the switch-side jumbo/L3 underlay change that unblocked the deploy. |
| `zero-to-vcap-vcf91-spine-build.md` | The blog post (markdown, draft) — the screen-by-screen narrative with the collapsed-TEP twist and the pool gotcha. |
| `screenshots-manifest.md` | Caption map + target filenames for the screenshots. |

## Headline lessons captured here
1. **The VCF wizard collapses the edge TEP onto the host TEP VLAN.** It does not expose a separate edge TEP VLAN — the field is read-only at the host VLAN. Planning a separate edge TEP VLAN (and routing it at jumbo) is avoidable work on this path; only the host TEP VLAN needs to carry jumbo.
2. **"Not enough IP addresses" on a large TEP pool = stale allocations, not a small pool.** Check IP Allocation; never shrink a range that has live allocations.
3. **Private TGW block must be a /16** in 9.1 — a /24 fails Supervisor/VKS.

## Still to add to this folder (binary — not generated here)
- **Screenshots** (`spine-s0*.png`, `meraki-0*.png`) — captured locally during the build; place them per `screenshots-manifest.md` so the markdown image links resolve.
- **Rendered Word versions** (`.docx`) of the blog posts, if you want them — produced in the working session; the markdown above is the git-native source for WordPress publishing.

## Open item
Verify the VLAN 32 DHCP scope on STACK 40GB does not overlap the edge TEP pool range `10.103.32.2–.16` (host TEPs use DHCP on the same subnet — overlap = silent duplicate IPs).
