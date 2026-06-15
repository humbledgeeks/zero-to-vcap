# VCF 9.1 NSX Spine Build — Session State & Resume Handoff

**Saved:** 2026-06-15 (corrected) · **Lab:** dc3 · **Domain:** humbledgeeks.com · **Console:** `dc3-vc01.humbledgeeks.com`

> **STATUS CORRECTION (2026-06-15):** an earlier version of this file said the next action was POST-3/SNAT and listed Step 4 deploy as remaining. That was stale and wrong. Per `runbook.md` (authoritative), the spine build is **COMPLETE through S22** — deploy, static route, HA VIP, SNAT, MX route flip, and the VPC connectivity profile are all done and confirmed. **Do NOT restart from Step 3/4.** Only S23 (N-S reachability) and the VI WLD wizard completion remain. Sections below are corrected.

## How to resume in a new chat
Start a new chat, attach (or reference) **this file** plus **`runbook.md`**, and say: *"Resume the VCF 9.1 NSX spine build — see the session-state doc."* Everything below is current as of this save.

---

## WHERE WE ARE RIGHT NOW
**The spine build is COMPLETE through S22.** All confirmed in `runbook.md`:
- Edge cluster `dc3-mgmt-edge-cl01` (2 edges, Up/Success) — S16
- Tier-0 `dc3-mgmt-t0-gw01`, VLAN 44 uplinks, both VPC IP blocks — Step 3
- Static default route `0.0.0.0/0 → 10.103.44.1` (S17), HA VIP `10.103.44.10/24` (S18), Provider Outbound SNAT on the External Connection (S19)
- MX static route flipped to the VIP: `10.103.50.0/24 → 10.103.44.10`
- Dashboard (S20), edge tunnels up (S21), and **the VPC connectivity profile EXISTS and is selectable** in the WLD wizard Step 9 (S22) — the payoff.

**Only open build item: S23 — north-south reachability** (procedure now in `runbook.md` under Validate).

**NEXT ACTION:** run S23, then complete the **VI WLD wizard** to deploy the workload domain + Supervisor with the now-populated profile (detail in `runbook.md` → "Then go back to the WLD wizard").

---

## STEP 3 — WHAT WAS FILLED AND CONFIRMED

| Field | Value confirmed in wizard |
|---|---|
| Gateway Name | `dc3-mgmt-t0-gw01` |
| High Availability Mode | Active Standby |
| BGP | **Off** (was defaulting On — toggled Off) |
| edge01 uplink | VLAN 44, `10.103.44.11/24` |
| edge02 uplink | VLAN 44, `10.103.44.12/24` |
| VPC External IP Block | `vpc-external-10.103.50.0-24` (10.103.50.0/24, Visibility=External) |
| Private TGW IP Block | `vpc-private-tgw-10.250.0.0-16` (10.250.0.0/16, Visibility=Private) |

### Step 3 lessons learned (blog-worthy)
- **VPC IP block fields are lookups, not free-text.** You must create the IP block objects in NSX Manager (Networking > IP Address Management > IP Address Blocks) BEFORE the wizard field will accept them. Typing a CIDR directly returns "No Items Found."
- **Day0 Private Tgw Ip Block is `172.31.0.0/16`** — AWS default VPC space, not your lab range. Do not use it. Created `vpc-private-tgw-10.250.0.0-16` (`10.250.0.0/16`, Private) as the correct replacement.
- **BGP defaults to On.** Toggle it Off for static routing — leaving it On forces an ASN field that blocks NEXT.
- **Next-hop is not set in the uplink modal.** The wizard has no next-hop field for static routing. The T0 default route (`0.0.0.0/0 → 10.103.44.1`) is a post-deploy step in NSX Manager.

---

## LOCKED DESIGN DECISION — collapsed edge TEP on VLAN 32
The consolidated VCF wizard **does not expose a separate edge TEP VLAN.** With "Use the host overlay network configuration" unchecked, the **TEP VLAN field stays read-only at 32**; only the IP pool is editable. We intended a separate edge TEP VLAN 42 and built the underlay for it — the wizard won't do it, so we went **collapsed on VLAN 32**.
- **VLAN 42 SVI + 32↔42 routing built in the underlay are now UNUSED scaffolding** — harmless, remove later.
- VLAN 32 carries jumbo end-to-end on STACK 40GB (9578). The per-node Run Check passed **"4 SUPPORTED HOSTS."**

## TROUBLESHOOTING RECORD — the TEP pool fix
- Edge 1 APPLY first failed: `[Fabric] Not enough IP address available in the given ip pool 525645af-… (Error code: 15000)` against pool `humbledgeeks-cl01-tep01`.
- Pool `10.103.32.0/24` (gw `10.103.32.1`) originally held two ranges `.2–.9` + `.10–.100` = **99 addresses** — far more than needed, so "not enough" meant **stale/leaked allocations** were filling it (from prior failed attempts).
- **Fix:** edited the subnet, removed the `.10–.100` range, leaving a single range **`10.103.32.2–10.103.32.16`** (15 addresses). Pool was confirmed **empty** at edit time, so the shrink was safe. Edge 1 then APPLIED — allocated from the fresh range.
- **OPEN SAFETY CHECK (still do this):** host TEPs pull from the **VLAN 32 DHCP scope on STACK 40GB** (`NSX32-HostTEP` SVI), same `10.103.32.0/24` subnet as this pool. **Confirm the DHCP scope does NOT overlap `.2–.16`** or edge TEPs (pool) and host TEPs (DHCP) collide — silent duplicate IPs. If it overlaps, exclude `.2–.16` from the DHCP scope or move the pool higher.

---

## AUTHORITATIVE VALUES (remaining build)

| Item | Value |
|---|---|
| Edge cluster | `dc3-mgmt-edge-cl01`, Tunnel Endpoint MTU **9000**, Form factor **Large**, auto-passwords ON |
| Edge node 1 | `dc3-nsx-edge01.humbledgeeks.com`, mgmt **10.103.16.138/24**, GW 10.103.16.1 — **DONE** |
| Edge node 2 | `dc3-nsx-edge02.humbledgeeks.com`, mgmt **10.103.16.139/24**, GW 10.103.16.1 — **DONE** |
| Cluster / Datastore / mgmt PG | `humbledgeeks-cl01` / `VMFS01` / `humbledgeeks-cl01-vds01-pg-vm-mgmt` (VLAN 16) |
| Edge TEP | **VLAN 32 (collapsed)**, IP Pool `humbledgeeks-cl01-tep01` range `10.103.32.2–.16`, gw 10.103.32.1 |
| Tier-0 | `dc3-mgmt-t0-gw01`, HA **Active/Standby**, routing **Static**, BGP Off |
| T0 uplink VLAN | **44**, edge1/edge2 uplink **10.103.44.11 / 10.103.44.12** /24, uplink MTU **1500** |
| T0 next hop (post-deploy) | `0.0.0.0/0 → 10.103.44.1` (static route added in NSX Manager post-deploy) |
| T0 HA VIP (post-deploy) | **10.103.44.10** |
| VPC External block | `vpc-external-10.103.50.0-24` — 10.103.50.0/24, Visibility=External |
| VPC Private TGW block | `vpc-private-tgw-10.250.0.0-16` — 10.250.0.0/16, Visibility=Private (/16 mandatory) |
| NSX IP blocks pre-created | Both blocks must exist in NSX Manager > IP Address Blocks BEFORE wizard will accept them |
| WLD handoff (SDDC Mgr) | DNS 10.103.20.11 / 10.103.20.12, domain humbledgeeks.com, control plane 10.103.16.65–.69, Private CIDR 10.244.0.0/16, NTP = dc3 time source |
| MX static route (post-deploy) | `10.103.50.0/24` next hop change **.44.11 → .44.10** (T0 VIP) once VIP exists |

---

## REMAINING STEPS
**Items previously listed here (Step 4 deploy, POST routing, MX flip, S20–S22) are DONE.** What actually remains:
1. **S23 — north-south reachability** (validation). Procedure is in `runbook.md` under Validate.
2. **Complete the VI WLD wizard** to deploy the workload domain + Supervisor with the now-populated VPC profile:
   - Step 5 — **Join existing** NSX `dc3-nsx01` (NOT create new — creating new orphans the spine).
   - Step 8 — host-TEP **static IP pool** `humbledgeeks-wld-host-tep01` (`10.103.32.20–.60`), **NOT DHCP**. One-shot; cannot change after deploy.
   - Step 9 — vSphere Supervisor: select **"Default VPC Connectivity Profile"**; Service CIDR off the TEP subnet (e.g. `10.96.0.0/24`); Control Plane `10.103.16.65–.69` (mgmt subnet); Private CIDR **/16** `10.244.0.0/16`; DNS .20.11/.12; domain humbledgeeks.com; NTP dc3.
   - Full field-by-field + traps in `runbook.md` → "Then go back to the WLD wizard."
3. **Open safety check (still do):** confirm the VLAN 32 DHCP scope does not overlap the edge TEP pool `.2–.16`.

## DELIVERABLES & BLOG (for the separate review chat)
- **Merged post:** `zero-to-vcap-vcf91-workload-domain-MERGED.md` (this folder). Accurate as saved — spine built, profile exists.
- **Word doc:** `Zero-to-VCAP-VCF91-Workload-Domain-MERGED.docx` — generated in Claude's outputs; download and drop into this folder (binary can't be written to the repo by the tooling).
- **Companion spine post:** `zero-to-vcap-vcf91-spine-build.md` (deep-dive; ends at the edge cluster).
- **OPEN ACCURACY QUESTION for the review chat:** the merged post's Phase 11 + intro imply the workload domain *deployed* and Supervisor stalled *after*. But the VPC dropdown is at WLD wizard **Step 9** and the WLD wizard is the **resume** action — i.e. the WLD likely stalled AT the Supervisor step *before* deploy, not after a clean deploy. Confirm which actually happened and fix Phase 11 / the intro to match.
- Still to do before publish: fill three `<!-- TODO: URL -->` placeholders (Part 1, spine post, underlay post); Phases 3/6/7 are screenshot-only headers; 13 referenced images not yet in the folder (see `screenshots-manifest.md`).

---

## SCREENSHOT INVENTORY
- `spine-s01-transit-gateways-tab.png`, `spine-s02-centralized.png`, `spine-s03-prerequisites.png`, `spine-s04-edge-cluster.png`
- `spine-s05-edge-node-mgmt-final.png` — collapsed mgmt form, vm-mgmt PG
- `spine-s06-tep-runcheck-pass.png` — TEP VLAN 32 + green "4 SUPPORTED HOSTS"
- `spine-s08-both-edges-added.png` — both edges in cluster list, "2 Nodes"
- `spine-s10-s13-step3-final.png` — **Step 3 complete: T0 name, HA, BGP Off, both uplinks, both VPC blocks selected**
- `spine-s-nsx-ip-blocks.png` — NSX Manager IP Address Blocks showing vpc-external and vpc-private-tgw objects
- (still to capture) Review/Deploy (S14/S15); deploy monitor (S16); static route (S17); HA VIP (S18); SNAT (S19); NSX after dashboard (S20); tunnels up (S21); VPC profile present (S22); reachability (S23)

See `screenshots-manifest.md` for the full caption map.
