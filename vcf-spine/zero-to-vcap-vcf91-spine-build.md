---
title: "Building the NSX Spine: From an Empty Dropdown to a Working Tier-0"
series: "Zero to VCAP"
status: draft
env: "VCF 9.1 · dc3 lab · HumbledGeeks.com"
---

# Building the NSX Spine: From an Empty Dropdown to a Working Tier-0

> **DRAFT** — built live while clicking through the deploy. Screenshots and values are from my dc3 lab. Image links resolve once the `spine-s0*.png` captures are placed in this folder.

In the last post I fixed the physical underlay so the NSX overlay could finally pass jumbo frames. That was the detour. This is the destination: building the NSX "spine" — the edge cluster and Tier-0 gateway — that turns an empty VPC connectivity profile into a real one, so the vSphere Supervisor wizard finally has something to select.

I'm writing this as I go, screen by screen, so you can see the actual fields and the actual order, not a sanitized after-the-fact version.

## What you're building (and why)

Five objects chain together, and the last one is the thing the Supervisor wizard is waiting on:

- **Edge node** — a purpose-built VM that does the routing, NAT, and load balancing NSX can't do inside a hypervisor. You deploy two for redundancy.
- **Edge cluster** — the pair of edge nodes grouped so services run active/standby across them. The cluster is the unit a Tier-0 binds to.
- **Tier-0 gateway (T0)** — the top of the NSX routing tree: the border router between your overlay and the physical underlay (VLAN 44 → the MX → the world). North-south and NAT happen here.
- **External connection** — the T0's actual attachment to the physical network: its uplinks on VLAN 44 and the static routes that point it at the world.
- **VPC connectivity profile** — the policy that says "VPCs here get external connectivity through this Tier-0 and these IP blocks." Until it's backed by a real T0 + external connection + IP blocks, it's an empty shell — which is exactly why the Supervisor dropdown was blank.

Two design choices worth knowing: **static routing, not BGP** (the MX's BGP support is limited; the HA VIP handles failover at L2), and an **Active/Standby T0** (required for the stateful services Supervisor layers on top).

## Where it lives: the Transit Gateways tab

You build all of this from the management vCenter (dc3-vc01), not raw NSX Manager — doing it here keeps the objects VCF-aware so SDDC Manager doesn't flag drift later.

![Transit Gateways tab](spine-s01-transit-gateways-tab.png)

The Default Transit Gateway already sits in the list, but every meaningful column reads *None* or *Not Set*. That row is the empty profile shell — no edge cluster, no Tier-0, no external connection behind it, which is precisely why the Supervisor wizard wouldn't accept it. **SETUP NETWORK CONNECTIVITY** launches the wizard that fills it in.

## Wizard step 1: Centralized Connectivity

![Centralized Connection](spine-s02-centralized.png)

Choose **Centralized Connection**. It attaches the Transit Gateway to a Tier-0 for external communication, and that Tier-0 hosts the stateful services Supervisor depends on. Distributed VLAN Connection wires VPC subnets straight to a physical VLAN with no Tier-0 — simpler, but no stateful services, so it can't carry a Supervisor.

## The prerequisites gate

![Networking Prerequisites](spine-s03-prerequisites.png)

Click NEXT and NSX throws up a Networking Prerequisites modal — an acknowledgment checklist that's essentially a recap of the underlay and DNS work. Select All unlocks Continue. The two BGP lines are conditional on dynamic routing; on a static design they don't apply.

## Step 2: defining the edge cluster

![Edge Cluster step](spine-s04-edge-cluster.png)

Cluster name `dc3-mgmt-edge-cl01`, and **Tunnel Endpoint MTU 9000** — that 9000 is the overlay frame size the edges push onto the TEP network. It's the entire reason the physical underlay had to do jumbo. Node Form Factor is **Large**. ADD the first node and CLONE it for the second.

## Adding the first edge node

![Add Node — management settings](spine-s05-edge-node-mgmt-final.png)

Most of this is identity and placement. Two fields matter:

**Port Group.** The wizard defaults to the host vmkernel management PG (`…-pg-esx-mgmt`). Change it to `…-pg-vm-mgmt`. Both ride VLAN 16, so esx-mgmt would technically work — but the edge is a VM appliance, like the NSX managers, and belongs on the VM-management PG with them, not the host vmkernel network.

**"Use the host overlay network configuration."** This one checkbox decides your entire TEP design — and it didn't behave the way I expected.

## The edge TEP twist: the wizard collapses it onto the host VLAN

Back in the prerequisites I'd planned a separate edge TEP VLAN (42), and the underlay post was largely about routing VLAN 32 (host TEP) to VLAN 42 (edge TEP) at jumbo on the switch stack. So my instinct was to uncheck "Use the host overlay network configuration" and set the edge TEP to VLAN 42 with its own pool.

Unchecking the box does expose the TEP fields — but the **TEP VLAN field is read-only**. It shows 32, inherited from the host TEP configuration, and there is no way to type 42. The only editable control is the IP pool.

> **The lesson:** this consolidated VCF wizard only builds the *collapsed* TEP model — the edge TEP shares the host TEP VLAN. A separate edge TEP VLAN is not an option on this path. To force one, you'd abandon this wizard and hand-build the edge transport nodes in NSX Manager with a custom uplink profile — which then risks the VCF integration this wizard exists to produce. In a single-rack management domain, that's not a trade worth making.

So I re-checked the box and went collapsed: edge TEP on VLAN 32, sharing the host TEP pool. Being honest, that means the separate VLAN 42 SVI and the 32↔42 routing from the underlay post are now unused scaffolding. They're harmless, and the jumbo work on VLAN 32 was still essential — but if I were doing this again I wouldn't split the TEP VLANs at all. **Part of the underlay wall I climbed was self-inflicted by choosing separate TEP VLANs the wizard never intended to support.**

## The Run Check: proving the jumbo island

![TEP VLAN 32 and a green Run Check](spine-s06-tep-runcheck-pass.png)

With the TEP on VLAN 32 and the host pool selected, the VLAN MTU Check returns a green **"4 SUPPORTED HOSTS."** That is the entire underlay detour paying off in one line — it passes only if VLAN 32 carries a 9000-byte frame, unfragmented, from the edge TEP across the STACK 40GB fabric to every host TEP, with the gateway on the jumbo stack, not the 1500-byte MX.

## The detour inside the detour: "not enough IP addresses"

APPLY didn't succeed the first time. NSX threw: *[Fabric] Not enough IP address available in the given ip pool … (Error code 15000)* — against the host TEP pool the edge was pulling from.

That was a head-scratcher, because the pool spanned roughly a hundred addresses on `10.103.32.0/24` — far more than four hosts plus two edges need. A pool that large reporting "not enough" almost always means stale or leaked allocations are sitting in it, usually from earlier failed attempts. IP Management → IP Allocation is where you confirm what's actually consuming it.

> **The fix, and the rule:** I trimmed the pool to a clean, genuinely unallocated range and the edge applied. Never shrink or remove a range on a TEP pool that has live allocations — you can orphan a running host TEP that way. Verify the pool is clear, or only add a fresh range, before you touch it. And when a pool that's obviously big enough says "not enough," believe the allocation table, not your mental math.

## Edge node 2: clone, don't retype

![Both edges in the cluster](spine-s08-both-edges-added.png)

The second edge is a clone of the first — change only the identity fields: name `dc3-nsx-edge02.humbledgeeks.com` and management `10.103.16.139/24`. Everything else, including the collapsed VLAN 32 TEP and the host pool, carries forward. Its Run Check came back green the same way, and APPLY put it in the list.

Two edges — the active/standby pair a Tier-0 needs for HA. Step 2 is done. NEXT moves into Workload Domain Connectivity.

## Step 3: Workload Domain Connectivity — three things the wizard gets wrong by default

This is where the Tier-0 gets its identity, its uplinks, and the VPC IP blocks. It's also where I hit three surprises in a row.

![Step 3 complete — T0 name, HA, BGP Off, uplinks, VPC blocks](spine-s10-s13-step3-final.png)

**Surprise one: BGP defaults to On.** The wizard opens with BGP toggled on and an ASN field marked required. For a static routing design this does nothing useful — but it blocks NEXT until you either fill the ASN or toggle BGP off. Toggle it off. The ASN field disappears and the routing section simplifies.

**Surprise two: the uplink modal has no next-hop field.** When you click Set on each edge's gateway uplinks (VLAN 44, `10.103.44.11/24` on edge01 and `10.103.44.12/24` on edge02, MTU 1500), there is no field to enter a next hop. For static routing, the T0 default route — `0.0.0.0/0 → 10.103.44.1` — is a post-deploy step in NSX Manager. The wizard only configures the interface, not the route.

**Surprise three: the VPC IP block fields are lookups, not free-text.** Typing `10.103.50.0/24` into the VPC External IP Blocks field returns "No Items Found." The wizard expects you to select a pre-existing IP block object from NSX. You have to create the blocks in NSX Manager first, then come back.

### Pre-creating the IP blocks in NSX Manager

![NSX Manager IP Address Blocks](spine-s-nsx-ip-blocks.png)

Path: Networking > IP Address Management > IP Address Blocks > Add IP Address Block. Two blocks needed:

| Name | CIDR | Visibility |
|---|---|---|
| `vpc-external-10.103.50.0-24` | `10.103.50.0/24` | External |
| `vpc-private-tgw-10.250.0.0-16` | `10.250.0.0/16` | Private |

The second one deserves a callout. NSX pre-creates a block called "Day0 Private Tgw Ip Block" — but it contains `172.31.0.0/16`, which is AWS default VPC space. Do not use it. Create your own `/16` block. In VCF 9.1, Supervisor carves TGW transit subnets from this range and requires a `/16` minimum — a `/24` will fail later at Supervisor deploy time with a cryptic carve error that has no obvious connection back to this screen.

With both blocks created, they appear in the wizard dropdowns. Select them, confirm the review screen, and click Deploy.

## Deploy: what's actually happening

![Review and Deploy](spine-s14-review.png)

![Deploy kicked off — Transit Gateways tab](spine-s15-transit-gw-in-progress.png)

The wizard clones both edge VMs into the management cluster (`humbledgeeks-cl01`, datastore `VMFS01`), registers them as NSX transport nodes, and creates the Tier-0 and its external connection. The Transit Gateways tab shows the banner immediately: "Request for setting up network connectivity is successfully submitted. The deployment of Edge Nodes is in progress."

![Edge Clusters — deploy in progress, OVF tasks visible](spine-s16-deploy-in-progress.png)

Watch the Edge Clusters view under Configure. Both edges clone simultaneously — Recent Tasks shows two "Deploy OVF template" tasks running in parallel at around 30% each. Total time in this lab: approximately 15 minutes.

![Edge Clusters — 2 Up, Success](spine-s16-deploy-complete.png)

When both columns go green — Node Connectivity Status "2 Up" and Status "Success" — the wizard's work is done. The T0 exists. The edge VMs are running. The overlay tunnels are up.

But the T0 still has no default route, no HA VIP, and no SNAT. None of those are set by the wizard for static routing. They are all post-deploy steps in NSX Manager.

## Post-deploy: the three things the wizard doesn't do

### POST-1 — Static default route

![T0 three-dot menu → Edit](spine-s17-t0-menu.png)

![T0 edit panel — ROUTING section, Static Routes > Set](spine-s17-t0-edit-routing.png)

Open the T0 edit panel (Networking > Tier-0 Gateways > three-dot menu > Edit), expand the ROUTING section, and click Set next to Static Routes.

![Set Static Routes modal — empty](spine-s17-static-routes-empty.png)

![ADD STATIC ROUTE row — name and network fields](spine-s17-add-route-row.png)

Click ADD STATIC ROUTE. The network field pre-populates with `0.0.0.0/0`. Give the route a name (`default-route-to-mx`) and click Set next to Next Hops.

![Set Next Hops — 10.103.44.1 / AD 1 being entered](spine-s17-next-hop-entry.png)

![Set Next Hops — saved, 10.103.44.1 confirmed](spine-s17-next-hop-saved.png)

Enter IP `10.103.44.1`, Admin Distance `1`. Click ADD, then APPLY. Back on the route row, click SAVE.

![Static route saved — green banner, status Uninitialized](spine-s17-route-added-uninitialized.png)

The green banner confirms the route was added. Status shows "Uninitialized" briefly — this is normal. It transitions to Success once the route is pushed to the edge dataplane.

![Static Routes list — default-route-to-mx, 0.0.0.0/0, Status Success](spine-s17-route-success.png)

Status Success means the route is programmed on the active edge. The T0 now has a way out: all traffic with no more-specific match goes to `10.103.44.1` — the MX SVI on VLAN 44.

### POST-2 — HA VIP

![T0 edit — HA VIP Configuration > Set](spine-s18-havip-set.png)

Still in the T0 edit panel, click Set next to HA VIP Configuration.

![Set HA VIP — empty](spine-s18-havip-empty.png)

![HA VIP entry — both External-interface44, 10.103.44.10/24, Enabled](spine-s18-havip-entry.png)

Click ADD HA VIP CONFIGURATION. Select both edge uplink interfaces (both show as `External-interface44` — one per edge). Enter IP/Mask `10.103.44.10/24`, toggle Enabled to Yes. Click ADD, then APPLY.

![HA VIP saved — External-interface44 x2, 10.103.44.10/24, Enabled Yes](spine-s18-havip-saved.png)

The VIP `10.103.44.10` now floats to whichever edge is active. This is the address the MX points at — once we update the static route from the interim `.44.11` to the VIP, edge failover becomes transparent to the MX.

![T0 updated — HA VIP = 1, Static Routes = 1, Changes Saved](spine-s18-t0-saved.png)

![T0 updated successfully banner](spine-s18-t0-confirmed.png)

The T0 now has both POST-1 and POST-2 in place: one static route, one HA VIP. The "Tier-0 Gateway dc3-mgmt-t0-gw01 updated successfully" banner confirms the save.

*… (draft continues: POST-3 outbound SNAT, MX route update, validation)*
