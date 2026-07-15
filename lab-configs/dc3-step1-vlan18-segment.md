# dc3 Workload VLAN Prep — Step 1 + Step 2 Quick Reference

## Step 1 — Create the VLAN 18 segment (Path 1, drift-free)

Log in to **NSX Manager** `dc3-nsx01.humbledgeeks.com` (the shared WLD NSX).

Navigate: **Networking** (top bar) → left nav **Segments** (under Connectivity) → **SEGMENTS** tab → **ADD SEGMENT**.

Fill exactly:

| Field | Value | Why |
|-------|-------|-----|
| Segment Name | `seg-vlan18-apps` | matches the plan |
| Connectivity | **None** | VLAN-backed L2 only. Do NOT select a T1 or T0. The MX `10.103.18.1` stays the gateway. |
| Transport Zone | `nsx-system-vlan-transport-zone` (type: VLAN) | already attached to the 4 WLD hosts |
| VLAN | `18` | single VLAN, not a range/trunk |
| Subnets / Gateway CIDR | **leave EMPTY** | no gateway in NSX; MX owns routing |
| Admin State | Up (default) | |

Click **SAVE**. When it asks *"Do you want to continue configuring this segment?"* click **NO** (no DHCP, no gateway, nothing else to add).

## Step 2 — Verify realization (this is the Path 1 vs Path 2 decision)

Check BOTH places. NSX status alone is not the signal.

**In NSX:**
- Segments list: `seg-vlan18-apps` Status goes to **Success / Up** (green).
- No realization alarm raised against the segment.
- Expand the segment status detail: all **4 WLD transport nodes** (`dc3-hst-esxi05-08`) show green.

**In vCenter `dc3-vc02` (the real signal):**
- Networking inventory → under VDS `wld-cls-vds-02`, an NSX port group named `seg-vlan18-apps` appears (shows as an NSX/opaque network).
- Edit a test VM's network adapter → `seg-vlan18-apps` is selectable.

### Verdict

- **Path 1 confirmed** if: segment Success on all 4 hosts **AND** the port group appears in `dc3-vc02` and is selectable on a VM NIC. Proceed to Step 3 (throwaway Ubuntu VM).
- **Go to Path 2** if: segment stuck In Progress / Down, throws a transport-node or realization alarm, **or** creates green in NSX but never appears in `dc3-vc02`. Then add the Default `nsx-vlan-transportzone` to the `wld-cls-vds-02` host switch via the Transport Node Profile (alongside the overlay TZ), which triggers a realization pass on the 4 hosts.
