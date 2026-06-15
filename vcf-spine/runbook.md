# VCF 9.1 — NSX Edge Spine Build Runbook (Management Domain)

Goal: build the edge cluster + Tier-0 + external connection + IP blocks so a **VPC connectivity profile** exists. That profile is what fills the empty dropdown in the WLD/Supervisor wizard.

**Where you do all of this:** the **Management Domain vCenter — `dc3-vc01.humbledgeeks.com`**. The edge cluster lives in the management domain (it's the routing/NAT spine for the whole fabric), so every object below lands on your **management cluster / management VDS / management datastore** — not the WLD's `dc3-vc02`.

Screenshots are tagged **S-NN**. **S07 (Run Check pass)** and **S20 (NSX after)** are the ones the blog needs most.

> **Underlay prerequisite is complete.** The jumbo TEP fabric is in place (VLAN 32 host+edge TEP routed on STACK 40GB at 9578, transit VLAN 99, VPC static route on the MX). The VLAN 42 SVI was also built but is **unused** — the wizard collapses the edge TEP onto VLAN 32 (see Phase C step 5). See `meraki-underlay-as-built.md` for that work. **S07 Run Check** proves VLAN 32 jumbo end-to-end.

---

## What you're building (and why) — read this first

Five objects chain together, and the last one is the thing the Supervisor wizard is waiting on:

- **Edge node** — a purpose-built VM that does the heavy network lifting NSX can't do inside a hypervisor: routing to the physical world, NAT, load balancing. You deploy two for redundancy.
- **Edge cluster** — the pair of edge nodes grouped together so services can run active/standby across them. The cluster is the unit a Tier-0 binds to.
- **Tier-0 gateway (T0)** — the top of the NSX routing tree. The border router between your overlay and the underlay (physical VLAN 44 → MX → world). North-south traffic and NAT happen here.
- **External connection** — the T0's actual attachment to the physical network: its uplinks on VLAN 44 and the static route that tells it where the world is.
- **VPC connectivity profile** — the policy object that says "VPCs created here get external connectivity through *this* Tier-0 and *these* IP blocks." Until it's backed by a real T0 + external connection + IP blocks, it's an empty shell — which is exactly why the Supervisor dropdown was blank.

The wizard builds the first four in one pass (Centralized Connectivity), and the result is a populated, usable connectivity profile.

Two design choices worth knowing:

- **Static routing, not BGP.** The MX's BGP support is limited, and a lab T0 with two static routes is simpler. Trade-off: no dynamic route failover — fine here because the HA VIP handles edge failover at L2.
- **Active/Standby T0.** Required for the stateful services Supervisor layers on top (NAT, LB). One edge active, one standby; the **HA VIP** is the single address the MX points at so it follows whichever edge is active.

---

## Two corrections baked into this runbook

1. **Private Transit Gateway block = `10.250.0.0/16`** (a /16, not `/24`). In 9.1 a /24 here fails VKS/Supervisor.
2. **TEP jumbo gate:** the host+edge TEPs are **collapsed onto VLAN 32** (the wizard does not expose a separate edge TEP VLAN — see Phase C step 5). VLAN 32 must carry jumbo end to end on STACK 40GB, gateway `10.103.32.1` on the jumbo stack, not the MX (1500). Run Check (S07) confirms it. **No 32↔42 routing is used** — the VLAN 42 SVI is now unused scaffolding (harmless; remove later).

---

## Authoritative spine values

| Item | Value |
|---|---|
| Console | MGMT vCenter `dc3-vc01.humbledgeeks.com` |
| Edge cluster name | `dc3-mgmt-edge-cl01` |
| Edge VM size | **Large** |
| Overlay MTU | `9000` (auto-pulled from NSX — just confirm) |
| Edge node 1 | `dc3-nsx-edge01.humbledgeeks.com`, mgmt **10.103.16.138/24**, GW 10.103.16.1 — **DONE** |
| Edge node 2 | `dc3-nsx-edge02.humbledgeeks.com`, mgmt **10.103.16.139/24**, GW 10.103.16.1 — **DONE** |
| Datacenter | `humbledgeeks-dc01` |
| vSphere cluster / datastore | `humbledgeeks-cl01` / `VMFS01` (VMFS6, 10 TB) |
| Mgmt Port Group (edge mgmt vNIC) | `humbledgeeks-cl01-vds01-pg-vm-mgmt` (**VLAN 16**) |
| Overlay / data VDS | `humbledgeeks-cl01-vds02` (DVUplinks-23) |
| DNS / domain | `10.103.20.11`, `10.103.20.12` / `humbledgeeks.com` |
| Edge TEP VLAN | **32** (collapsed onto host TEP VLAN — wizard does not expose a separate edge TEP VLAN) |
| Edge TEP IP assignment | **IP Pool** — host pool `humbledgeeks-cl01-tep01` (re-check "use host overlay config") |
| Edge TEP CIDR / gateway | 10.103.32.0/24 / **10.103.32.1** (host TEP subnet; gateway on STACK 40GB) |
| ~~Edge TEP pool `dc3-edge-tep-pool` / 10.103.42.11–.20~~ | **Not used.** Wizard pins edge TEP to VLAN 32. VLAN 42 SVI now unused scaffolding. |
| Tier-0 name | `dc3-mgmt-t0-gw01` |
| Tier-0 HA mode | **Active/Standby** (required for Supervisor) |
| Routing type | **Static** |
| Uplink VLAN | **44** (one uplink per edge) |
| Edge1 / Edge2 uplink IP | **10.103.44.11/24** / **10.103.44.12/24** |
| Uplink next hop (MX SVI) | **10.103.44.1** |
| Uplink interface MTU | **1500** (match the MX) |
| T0 HA VIP (post-deploy) | **10.103.44.10** |
| T0 default route (post-deploy) | `0.0.0.0/0 → 10.103.44.1` |
| VPC External IP block | **10.103.50.0/24**, visibility **Public** |
| Private TGW IP block | **10.250.0.0/16** (/16!) |
| MX static route | `10.103.50.0/24 → 10.103.44.10` (the VIP) |

---

## Pre-flight gates — ALL CLEARED

- [x] DNS forward + reverse for `dc3-nsx-edge01` (.138) and `dc3-nsx-edge02` (.139) — created and confirmed
- [x] VLAN 42 and 44 SVIs exist at .1; VLAN 42 DHCP excludes .11–.20 (42 SVI on STACK 40GB; 44 on MX) — see `meraki-underlay-as-built.md`
- [x] **L3 gateways for VLAN 32 and 42 are on STACK 40GB (9578), not the MX** — via transit VLAN 99; default route on the stack points to the MX
- [x] MX static route staged at `10.103.50.0/24 → 10.103.44.11` (interim — swap to VIP `.10` post-deploy)
- [x] Management cluster `humbledgeeks-cl01`, datastore `VMFS01`, mgmt PG `humbledgeeks-cl01-vds01-pg-vm-mgmt` (VLAN 16) confirmed

### DNS records (created)

| Record | Zone | Value |
|---|---|---|
| A | humbledgeeks.com (fwd) | `dc3-nsx-edge01` → 10.103.16.138 |
| A | humbledgeeks.com (fwd) | `dc3-nsx-edge02` → 10.103.16.139 |
| PTR | 16.103.10.in-addr.arpa | 138 → dc3-nsx-edge01.humbledgeeks.com |
| PTR | 16.103.10.in-addr.arpa | 139 → dc3-nsx-edge02.humbledgeeks.com |

*Why DNS matters:* NSX registers edge nodes by FQDN and checks forward + reverse during deploy. A missing PTR is a classic cause of a hung/vague-error deploy.

---

## Build (MGMT vCenter `dc3-vc01`) — Wizard

**Open the wizard:** vCenter object > **Networks** > **Transit Gateways** > **Setup Network Connectivity**. 4-step wizard:
1. Transit Gateway Connectivity (Centralized) → Networking Prerequisites modal (acknowledge, Select All, Continue)
2. Edge Cluster (cluster + nodes + TEP + Run Check)
3. Workload Domain Connectivity (Tier-0 + uplinks + VPC blocks)
4. Review and Deploy

- [x] **S01** — Transit Gateways tab before config
- [x] **S02** — Centralized Connectivity
- [x] **S03** — Networking Prerequisites modal (Select All → Continue; BGP/ASN lines are N/A for static)

**3 — Edge cluster**
- [x] Name `dc3-mgmt-edge-cl01`, size **Large**, confirm overlay **MTU 9000**.
  - [x] **S04** — edge cluster name / size / MTU ("Tunnel Endpoint MTU" = 9000)

**4 — Edge node 1**
- [x] Name `dc3-nsx-edge01.humbledgeeks.com`; cluster `humbledgeeks-cl01`; datastore `VMFS01`; Static; Management CIDR **10.103.16.138/24**; GW **10.103.16.1**; Port Group `humbledgeeks-cl01-vds01-pg-vm-mgmt`
  - [x] **NOTE (applied):** wizard defaults Port Group to `...-pg-esx-mgmt` (host vmkernel PG). Change to `...-pg-vm-mgmt` — the edge is a VM appliance, belongs with the NSX managers, not the host vmkernel PG.
  - [x] **S05** — edge node 1 mgmt fields (collapsed, vm-mgmt)

**5 — Edge node 1 TEP** *(the wizard forces the design here)*

> **Design decision — collapsed edge TEP on VLAN 32 (forced by the wizard).**
> We intended a separate edge TEP VLAN (42) and built the underlay for it. **The consolidated VCF wizard does not support that.** With "use host overlay configuration" unchecked, the **TEP VLAN field is read-only and stays 32** — only the IP Pool is editable. This wizard only builds the *collapsed* model: edge TEP shares the host TEP VLAN. Forcing 42 would mean hand-building edge transport nodes in NSX Manager with a custom uplink profile — which jeopardizes the VPC connectivity profile this wizard produces. **We go collapsed on VLAN 32.** The VLAN 42 SVI + 32↔42 routing are now unused (harmless).

- [x] **Re-check** "Use the host overlay network configuration." Restores TEP **VLAN 32**, host pool `humbledgeeks-cl01-tep01`.
- [x] Confirm host pool has free IPs for the two edge TEPs.
  - [x] **S06** — Edge TEP VLAN 32 + host pool

**6 — Run Check (MTU)**
- [x] Click **Run Check** — must pass.
  - [x] **S07** — Run Check passing: "4 SUPPORTED HOSTS" *(key blog shot)*

> **Troubleshooting — "[Fabric] Not enough IP address available … (Error code 15000)" on APPLY.**
> Edge 1's first APPLY failed against pool `humbledgeeks-cl01-tep01` even though it spanned `.2–.100` (99 addresses). Cause: **stale/leaked TEP allocations** from prior failed attempts. Fix: NSX Manager → **IP Management → IP Address Pools** → edit subnet → remove the stale range (`.10–.100`), leaving `10.103.32.2–10.103.32.16` (pool confirmed empty first, so safe). Edge 1 then APPLIED. **Never shrink/remove a range with live allocations** — only add ranges. **Open check:** ensure the VLAN 32 DHCP scope on STACK 40GB does not overlap `.2–.16` (host TEPs use DHCP on the same subnet — overlap = duplicate IPs).

**7 — Edge node 2 (clone)**
- [x] Select edge 1 > **Clone**. Name `dc3-nsx-edge02.humbledgeeks.com`, Management CIDR **10.103.16.139/24**. **Apply**.
- [x] Verify clone kept TEP **VLAN 32**, host pool, box **checked**.
  - [x] **S08** — both edges added, "2 Nodes"

**8 — Edge passwords**
- [x] Auto-generate (ON — managed via SDDC Manager)
  - [ ] **S09** — password page (redact before publishing)

---

> ### ✅ STATUS — Wizard Step 2 (Edge Cluster) COMPLETE
> Both edges in the cluster list (`dc3-nsx-edge01` + `dc3-nsx-edge02`, **"2 Nodes"**), cluster `dc3-mgmt-edge-cl01`, MTU 9000, Large, auto-passwords ON. Collapsed TEP VLAN 32, pool `.2–.16`. Run Checks green.
> **VLAN 32 DHCP scope confirmed clear** — DHCP removed from MX for VLAN 32; no overlap with TEP pool `.2–.16`. ✅

---

> ### ✅ STATUS — Wizard Step 3 (Workload Domain Connectivity) COMPLETE
> - Gateway Name `dc3-mgmt-t0-gw01`, HA Active/Standby, BGP **Off**, routing Static.
> - Edge01 uplink: VLAN 44, `10.103.44.11/24`. Edge02 uplink: VLAN 44, `10.103.44.12/24`. MTU 1500.
> - VPC External block: `vpc-external-10.103.50.0-24` (10.103.50.0/24, Visibility=External) — pre-created in NSX Manager IP Address Blocks.
> - Private TGW block: `vpc-private-tgw-10.250.0.0-16` (10.250.0.0/16, Visibility=Private) — pre-created in NSX Manager. Day0 block (`172.31.0.0/16`) was AWS default space; not used.
> - Review screen confirmed all fields. **DEPLOY clicked → Step 4 in progress.**
>
> **Lessons learned (blog-worthy):**
> - BGP defaults to On — must toggle Off for static routing or NEXT is blocked by mandatory ASN field.
> - VPC IP block fields are lookups, not free-text — blocks must exist in NSX Manager > IP Address Blocks before the wizard accepts them.
> - No next-hop field in the uplink modal for static routing — T0 default route is a post-deploy step in NSX Manager.
> - Day0 Private Tgw Ip Block = `172.31.0.0/16` (AWS space) — always replace with your own /16 block.
> **RESUME HERE → monitor deploy, then post-deploy steps below.**

---

**9 — Tier-0 gateway** ✅ DONE
- [x] Name `dc3-mgmt-t0-gw01`; HA mode **Active/Standby**; BGP **Off**; Routing = **Static**.
  - [x] **S10** — Tier-0 name + HA mode + BGP Off

**10 — Uplinks (one per edge, VLAN 44)** ✅ DONE
- [x] Edge1 uplink: VLAN **44**, IP **10.103.44.11/24**, MTU **1500**
- [x] Edge2 uplink: VLAN **44**, IP **10.103.44.12/24**, MTU **1500**
  - [x] **S11** — both edge uplinks on VLAN 44

*Why:* These are the T0's physical-facing interfaces on VLAN 44, which stays on the MX, so MTU **1500** (ordinary routed traffic, not overlay). Each edge gets its own uplink IP; the shared VIP comes later. **Note: the wizard has no next-hop field for static routing — that is POST-1 below.**

**11 — VPC IP blocks** ✅ DONE
> **Pre-req discovered:** IP block objects must be created in NSX Manager > Networking > IP Address Management > IP Address Blocks BEFORE this step. The wizard fields are lookups — typing a CIDR returns "No Items Found."

- [x] Created `vpc-external-10.103.50.0-24` in NSX Manager (10.103.50.0/24, Visibility=External). Selected in wizard.
  - [x] **S12** — external block selected
- [x] Created `vpc-private-tgw-10.250.0.0-16` in NSX Manager (10.250.0.0/16, Visibility=Private). Selected in wizard. Day0 block removed.
  - [x] **S13** — private TGW block /16 selected

**12 — Review & Deploy** ✅ DONE
- [x] Reviewed: Cluster `dc3-mgmt-edge-cl01`, 2 nodes, Large, Gateway `dc3-mgmt-t0-gw01`, Active Standby, BGP Off, both IP blocks confirmed.
  - [x] **S14** — review summary
- [x] **S15** — deploy started. Banner: "Request for setting up network connectivity is successfully submitted. The deployment of Edge Nodes is in progress." Transit Gateways tab shows `Default Transit Gateway`, Connection=Centralized, HA=Active Standby, Status=In Progress.

**13 — Monitor**
- [x] Watch **Configure > Networking > Edge Clusters**. ~20 min. OVF deploy tasks visible in Recent Tasks (~32–34% at start).
  - [x] **S16** — edge cluster complete. Node Connectivity Status **2 Up**, Status **Success**. Both edges confirmed up after page refresh.

---

## Post-deploy — static routing (NSX Manager `dc3-nsx01`)

Centralized + static doesn't auto-add a default route or HA VIP:

- [x] **Networking > Connectivity > Tier-0 Gateways** > three-dot menu > **Edit** > expand **ROUTING** > **Static Routes > Set** > ADD STATIC ROUTE
  - Name: `default-route-to-mx`, Network: `0.0.0.0/0`, Next Hop: **10.103.44.1**, Admin Distance: **1**
  - Status transitions: Uninitialized → **Success** (pushed to active edge dataplane)
  - [x] **S17** — static route `default-route-to-mx`, 0.0.0.0/0, Next Hops 1, Status Success

- [x] Same T0 edit > **HA VIP Configuration > Set** > ADD HA VIP CONFIGURATION
  - Interfaces: both **External-interface44** uplinks (one per edge)
  - IP Address/Mask: **10.103.44.10/24**, Enabled: **Yes**
  - [x] **S18** — HA VIP 10.103.44.10/24, Enabled Yes; T0 save confirmed with banner "Tier-0 Gateway dc3-mgmt-t0-gw01 updated successfully"; HA VIP = 1, Static Routes = 1

  > **Note:** Both POST-1 and POST-2 were saved in the same T0 edit session — banner confirms both persisted.

- [x] **VPC Connectivity > External Connections** > `Gateway-connection-dc3-mgmt-t0-gw01` > Edit > Advanced Settings:
  - Toggle **Provider Outbound SNAT** = On
  - **External IP Blocks** = `vpc-external-10.103.50.0-24` (REQUIRED — without it, SAVE fails with error 640103 "NAT config ip_block must be present when SNAT is enabled")
  - SNAT IP Blocks field left empty at save time — after save, NSX auto-populated it with `vpc-external-10.103.50.0-24` (derived from the External IP Block selection)
  - [x] **S19** — SNAT On, External IP Block + SNAT IP Block both = `vpc-external-10.103.50.0-24`, banner "Centralized External Connection ... updated successfully"

  > **Gotcha:** SNAT in 9.1 is on the **External Connection** (VPC Connectivity > External Connections), NOT in the T0 edit panel. And enabling SNAT requires an External IP Block selected on the same connection — the SNAT IP Blocks dropdown is a separate (empty) object type and is not what the error asks for.

*Why:* No default route = T0 has no way out (`0.0.0.0/0 → 10.103.44.1` = MX SVI). VIP = single floating address the MX points at, follows the active edge. SNAT off by default = egress keeps private source IP, MX has no return path, connections hang.

---

## MX — point the route at the VIP

- [x] Update MX static route to `10.103.50.0/24 → 10.103.44.10` (the VIP). If staged on `.11`, change it now so it follows failover.
  - [x] Confirmed: route row reads `10.103.44.10`, NSX External Connection status = Success

---

## Validate

- [x] NSX **Home > Overview** shows **1 Tier-0, 1 External Connection, 2 Edges**
  - [x] **S20** — NSX "after" dashboard: 1 Tier-0, 1 External Connection, 1 Transit Gateway, 2 Segments, 1 Edge Cluster (2 nodes), 1 Host Cluster / 4 Hosts. Note: 0 NAT Rules is correct — provider outbound SNAT lives on the external connection, not as a NAT rule.
- [x] T0 status Success/Up; overlay tunnels up (host TEP ↔ edge TEP, both VLAN 32)
  - [x] **S21** — tunnels up. Checked on the EDGE side (System > Fabric > Edges), which is authoritative. Edge cluster `dc3-mgmt-edge-cl01` = 2 Up / Success. edge01 (mgmt .138, TEP 10.103.32.10) and edge02 (mgmt .139, TEP 10.103.32.12) each show **Tunnels ↑4** (one per host), Connectivity Up, Status Success.
  - Note: the host-side Tunnels column (System > Fabric > Hosts) read "Not Available" — that is a display quirk on the host view, NOT a failure. Edge↔host tunnels come up when the edge joins the overlay TZ, not on tenant traffic. Edge TEPs on 10.103.32.x confirm the VLAN 32 collapsed design + tep01 pool work end to end.
- [x] A **VPC connectivity profile** now exists in the Default project
  - [x] **S22** — confirmed via the WLD wizard: Step 9 vSphere Supervisor shows NSX Project `Default` → VPC Connectivity Profile dropdown populated with **"Default VPC Connectivity Profile"**. This is the payoff — the dropdown that was empty at the start is now selectable.
- [ ] North-south reachability through the MX
  - [ ] **S23** — reachability. Run in order; stop at first failure:
    1. **Uplink to next hop:** SSH active edge (`admin`) → `get logical-routers` → `vrf <t0-sr-id>` → `ping 10.103.44.1` (MX SVI). Or UI: Tier-0 > Interfaces, both `External-interface44` Up.
    2. **Northbound egress (route + SNAT):** from the same edge VRF, `ping <upstream/external IP>` beyond the MX. Fail = check SNAT on External Connection + MX return route to `10.103.50.0/24`.
    3. **Return to VIP:** from another VLAN or the MX, `ping 10.103.44.10` (HA VIP). Proves MX→spine + the `10.103.50.0/24 → .44.10` next hop is live.
    4. **HA failover:** continuous ping the VIP, then maintenance-mode/reboot the active edge → VIP moves to standby, pings resume in seconds.
    5. **UI alt:** Plan & Troubleshoot > Traceflow — inject from a VPC/overlay segment to an external IP, watch segment → T0 SR → uplink.
    - Final acceptance (deferred, needs a tenant workload): a VM on a VPC segment egresses (SNAT to `10.103.50.x`) and gets a reply — record after Supervisor deploys.

---

## Then go back to the WLD wizard

### VI WLD wizard — Step 5 NSX Manager
- **Join existing NSX Manager instance** → `dc3-nsx01` (NOT create new). Reusing the existing NSX is what lets this WLD see the VPC connectivity profile built above. Creating a new NSX would orphan the entire spine.
- The two yellow warnings (NSX shared across SSO domains / VPCs span connected WLDs) are informational, not blockers in the lab.

### VI WLD wizard — Step 8 Distributed Switch (host TEP) — CONFIRMED against VCF 9.1 docs
- Profile: **NSX Traffic Separation** (custom) — two VDS: `wld-cls-vds-01` (mgmt/vMotion, vmnic0/1), `wld-cls-vds-02` (NSX-Overlay, vmnic2/3).
- NSX-Overlay edit dialog:
  - Transport Zone: `overlay-tz-mgmt-nsxt` (inherited from joined NSX), MTU 9000
  - **Transport VLAN: 32** (ESX host TEP VLAN; confirmed trunked to vmnic2/3)
  - **IP Assignment (TEP): change DHCP → Static IP Pool** — DO NOT use DHCP. DHCP was removed from VLAN 32 (edge pool collision avoidance); a DHCP-set host TEP would get no answer → APIPA 169.254.x → overlay breaks.
    - New pool `humbledgeeks-wld-host-tep01`: CIDR `10.103.32.0/24`, Gateway `10.103.32.1` (the VLAN 32 SVI — KEEP IT, the pool requires it), Range `10.103.32.20–10.103.32.60` (clears `.1` gateway + edge pool `.2–.16`)
  - Map both NSX uplinks → VDS uplinks; uplink profile teaming = **Load Balance Source**

  > **Gotcha #1 (myth busted):** On a Meraki MX, the SVI (gateway `.1`) and DHCP are independent per-VLAN settings. Turning DHCP off did NOT require removing the SVI, and removing the SVI would break the gateway the static pool + edges depend on. Do not remove it.
  > **Gotcha #2 (one-shot):** Host TEP DHCP→static-pool generally CANNOT be changed in the UI after WLD deploy. Set static pool now; there is no clean fix-later path.
  > Static pool is only editable on a custom profile; the pure default profile locks you into DHCP. NSX Traffic Separation = custom = editable. Good.

### VI WLD wizard — Step 9 vSphere Supervisor

SDDC Manager > **+ WORKLOAD DOMAIN > VI - Workload Domain** > step 9 vSphere Supervisor. The **VPC Connectivity Profile** dropdown is now populated — select **"Default VPC Connectivity Profile"** (NSX Project = `Default`).

Field-by-field (with the traps that cost time):
- **Supervisor Name:** `dc3-mgmt-supervisor`
- **Service CIDR:** internal K8s ClusterIP range — use a DEDICATED unused block, e.g. `10.96.0.0/24`. **DO NOT** use `10.103.32.0/24` — that's the TEP subnet; reusing a real infra subnet here invites routing conflicts.
- **Use ESXi Management VMK settings:** checked → control plane MUST live in the management subnet `10.103.16.0/24`.
- **Control Plane IP Range:** `10.103.16.65–10.103.16.69` (5 consecutive free IPs in mgmt subnet). If you put it in `10.103.32.x` you get the red error "IP range does not belong to the same subnet as the Management network."
- **VPC Connectivity Profile:** `Default VPC Connectivity Profile`
- **Private CIDR:** must be a **/16** (a /24 fails Supervisor). Planned value `10.244.0.0/16`. (Wizard had defaulted to `172.30.0.0/16` — both are valid private /16s outside the 10.103.x infra; pick deliberately.) **OPEN QUESTION:** unconfirmed whether this Private CIDR must align with the NSX private-TGW block `10.250.0.0/16` or is independent — verify in VCF 9.1 docs if Validation flags the private space.
- **Workload DNS:** `10.103.20.11`, `10.103.20.12`
- domain `humbledgeeks.com`, NTP = dc3 time source

  > **Gotcha (root cause of two errors):** the `.32` TEP subnet got reused for both Service CIDR and Control Plane Range. Service CIDR and Control Plane must each be off the TEP subnet — Service CIDR on a dedicated internal block, Control Plane in the management subnet.

*Why:* The moment the entire detour was for. The dropdown that was empty at the start now has exactly one correct option, and the Supervisor deploy can proceed.
