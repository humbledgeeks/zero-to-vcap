# Screenshot Manifest — vcf-spine

The captures used by `zero-to-vcap-vcf91-spine-build.md` and `meraki-underlay-as-built.md`. The originals are on this Mac (from when they were taken); drop them into this folder under the filenames below and the markdown image links resolve. The two `*-mgmt.png` / `*-edge1-*.png` intermediate shots are optional.

## Spine build (used by the spine blog post)

| Filename | Caption / what it shows | Status |
|---|---|---|
| `spine-s01-transit-gateways-tab.png` | Transit Gateways tab — Default TGW empty shell (None / Not Set) | captured |
| `spine-s02-centralized.png` | Wizard step 1 — Centralized Connection selected | captured |
| `spine-s03-prerequisites.png` | Networking Prerequisites acknowledgment modal | captured |
| `spine-s04-edge-cluster.png` | Edge Cluster step — name, Tunnel Endpoint MTU 9000, Large | captured |
| `spine-s05-edge-node-mgmt-final.png` | Add Node — mgmt on pg-vm-mgmt, host-overlay box checked (collapsed) | captured |
| `spine-s06-tep-runcheck-pass.png` | TEP VLAN 32 + host pool, VLAN MTU Check green "4 SUPPORTED HOSTS" | captured |
| `spine-s08-both-edges-added.png` | Both edges in cluster list — "2 Nodes", Step 2 complete | captured |

### Still to capture (Step 3 onward)
| Filename | What it should show |
|---|---|
| `spine-s10-tier0-name-ha.png` | Tier-0 `dc3-mgmt-t0-gw01`, HA Active/Standby, Static |
| `spine-s11-uplinks-vlan44.png` | Both edge uplinks on VLAN 44 (.44.11 / .44.12, MTU 1500) |
| `spine-s12-vpc-external-block.png` | VPC External block 10.103.50.0/24, visibility Public |
| `spine-s13-private-tgw-block.png` | Private TGW block 10.250.0.0/16 (/16) |
| `spine-s14-review.png` | Review summary |
| `spine-s16-deploy-complete.png` | Edge cluster deployed |
| `spine-s17-t0-default-route.png` | T0 static default route 0.0.0.0/0 → 10.103.44.1 |
| `spine-s18-ha-vip.png` | HA VIP 10.103.44.10 |
| `spine-s20-nsx-after.png` | NSX Overview: 1 Tier-0 / 1 External / 2 Edges |
| `spine-s21-tunnels-up.png` | Overlay tunnels up |
| `spine-s22-connectivity-profile.png` | VPC connectivity profile present (the payoff) |

## Underlay (used by meraki-underlay-as-built.md)

| Filename | What it shows |
|---|---|
| `meraki-00-mx-dhcp-reservations.png` | MX DHCP reserved ranges |
| `meraki-01-mx-static-route.png` | MX NSX-VPC-External static route |
| `meraki-02-defaultgw-error.png` | "first L3 interface needs defaultGateway" error |
| `meraki-03-transit-and-vlan42.png` | Transit VLAN 99 + VLAN 42 SVI + auto default route |
| `meraki-04-mx-vlan32-dhcp.png` | MX VLAN 32 DHCP scope (pre-cutover) |
| `meraki-05-all-three-interfaces.png` | Final: three SVIs on STACK 40GB |

> Reminder: redact any password page before publishing (S09 is intentionally not in the post).
