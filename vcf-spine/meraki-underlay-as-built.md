# VCF 9.1 Underlay Fix — Routing NSX TEP Traffic on the Switch (Meraki As-Built)

*dc3 / humbledgeeks.com — as-built record of the Meraki underlay change that unblocks the NSX edge deploy.*

> Image links below resolve once the `meraki-00…05.png` screenshots are placed in this folder (they were captured locally during the build).

---

## The problem

NSX GENEVE overlay needs an MTU of **≥1600**. In dc3 the **MX is the L3 gateway for every VLAN at 1500** and can't go higher. The switches are a different story — **STACK 40GB (MS425-32) runs at 9578**, and all the UCS Fabric Interconnects and ESXi/HCI hosts land on it.

So the host TEP (VLAN 32) ↔ edge TEP (VLAN 42) traffic, which has to be inter-VLAN routed, was being routed by the one device in the path that *can't* do jumbo. The edge deploy Run Check would have failed on overlay MTU.

**Fix:** move the L3 gateways for the two TEP VLANs (32 and 42) off the MX and onto STACK 40GB, where they route at jumbo. Everything else stays.

> **Postscript (discovered during the spine build):** the consolidated VCF wizard collapses the edge TEP onto the **host** TEP VLAN (32) and does not expose a separate edge TEP VLAN. So the VLAN 42 SVI and the 32↔42 routing built here ended up **unused** — VLAN 32 jumbo (which this work also delivered) is what the deploy actually relies on. See `runbook.md` Phase C step 5. The jumbo-on-the-switch lesson stands; the separate-VLAN split was avoidable.

---

## What moved, what stayed

| VLAN | Role | L3 gateway | MTU | DHCP |
|---|---|---|---|---|
| 32 | Host TEP (and edge TEP, collapsed) | **STACK 40GB** `10.103.32.1` | 9578 | Switch SVI |
| 42 | Edge TEP (built, **unused**) | **STACK 40GB** `10.103.42.1` | 9578 | None |
| 99 | Transit (switch↔MX) | switch `.2` / MX `.1` `10.103.99.0/30` | — | None |
| 44 | Edge uplink (north-south) | **MX** `10.103.44.1` | 1500 | MX |
| 16 | Management | **MX** `10.103.16.1` | 1500 | MX |

The VLAN IDs did **not** change. Only the device answering for `.1` moved. No NSX reconfiguration was required.

---

## Decision: the VPC-External static route stays on the MX

`NSX-VPC-External: 10.103.50.0/24 → 10.103.44.11` (next hop becomes the T0 VIP `.10` once it exists)

![MX static route](meraki-01-mx-static-route.png)

**Why the MX and not the switch:** the next hop is in **VLAN 44**, and only the MX has an interface there. The switch can't use `.11` as a next hop — the route would be invalid. Anything on the switch destined for `10.103.50.0/24` follows the switch's default route to the MX, which holds the specific route.

---

## Build walkthrough

### Starting state — MX DHCP reservations

![MX DHCP reserved ranges](meraki-00-mx-dhcp-reservations.png)

VLAN 42 and VLAN 44 each reserve `.2–.20`. (VLAN 42's became moot once 42 moved off the MX; VLAN 44's still protects the VIP `.10` and uplinks `.11/.12`.)

### The gotcha — the first switch L3 interface demands a default gateway

![defaultGateway required error](meraki-02-defaultgw-error.png)

> *For the first layer 3 interface, parameter 'defaultGateway' is required.*

Meraki requires the **first** L3 interface on a switch/stack to carry the route of last resort. The TEP VLANs are an isolated island with no upstream router, so neither 32 nor 42 can be "first."

**The fix:** make a tiny **transit interface to the MX** the first L3 interface. It has a real default gateway (the MX), satisfying the requirement. The TEP VLANs come in second and third with no gateway prompt. This does **not** reintroduce the MTU problem — 32↔42 ride the switch's directly-connected jumbo routes and never touch the transit.

### Transit (VLAN 99) + Edge TEP (VLAN 42)

1. **MX** → create VLAN 99 (`NSX-TRANSIT`), `10.103.99.0/30`, MX IP `10.103.99.1`, no DHCP.
2. **STACK 40GB** → Routing & DHCP → Add interface → first = VLAN 99, IP `10.103.99.2`, **Uplink gateway `10.103.99.1`** (auto-creates the switch default route).
3. **STACK 40GB** → add VLAN 42, IP `10.103.42.1/24`, uplink gateway blank, DHCP off.

![Transit + VLAN 42 + default route](meraki-03-transit-and-vlan42.png)

### Host TEP (VLAN 32) — the live cutover

VLAN 32 was already serving DHCP to deployed host TEPs. Rule: **delete from the MX first, then build on the switch**, so VLAN 32 never has two `.1` gateways or two DHCP servers at once.

![MX VLAN 32 DHCP settings](meraki-04-mx-vlan32-dhcp.png)

1. **MX** → delete VLAN 32 (NSX32).
2. **STACK 40GB** → add VLAN 32, IP `10.103.32.1/24`, **Run a DHCP server** mirroring the MX (1-day lease, proxy/dc3 DNS, no reservations).

Existing host TEPs kept leases and gateway IP (`.1` unchanged), re-ARPed to the switch, no NSX change needed.

### Final state — three interfaces on STACK 40GB

![All three interfaces created](meraki-05-all-three-interfaces.png)

- `NSX-Transit-Uplink` — VLAN 99, `10.103.99.2/30`, DHCP off
- `NSX42-EdgeTEP` — VLAN 42, `10.103.42.1/24`, DHCP off
- `NSX32-HostTEP` — VLAN 32, `10.103.32.1/24`, DHCP **Server**
- Default route `0.0.0.0/0 → 10.103.99.1` (switch → MX)

---

## Validation

```
vmkping ++netstack=vxlan -d -s 8972 10.103.32.1
```

Success at 8972 bytes with DF set confirms the host-TEP-to-switch-SVI path is jumbo-clean. **Definitive proof** is the edge deploy **Run Check** ("4 SUPPORTED HOSTS").

---

## Two lessons worth keeping

1. **Meraki's "first L3 interface needs a default gateway" forces a transit.** Standing up an isolated routed island on an MS stack: give the stack a real uplink to its upstream router first, then add the island VLANs.
2. **Put a static route where its next hop is directly connected.** The VPC-External route belongs on the MX because the T0 next hop lives in an MX-owned VLAN.
