# Image Order — VCF 9.1 Workload Domain + NSX Spine

Screenshots were captured in **reverse** order. They have been renamed into true
chronological workflow order (`vcf91-wld-NNN-*.jpg`). Mapping below: new name →
what it shows → original capture name. The rename script is `../rename-images.sh`.

## Act 1 — The environment & the wall (NSX/vCenter "before")
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 001 | nsx-overview-before | NSX Overview: 0 Tier-0, 0 External Connections, 0 Segments, 1 empty Transit Gateway | vcf_117 |
| 002 | transit-gateway-empty-shell | Default Transit Gateway: Connectivity Not Set, 0 External Connections, 0 VPCs | vcf_84 |
| 003 | vpc-get-started | VPC "Get Started" — Setup Network Connectivity not done | vcf_83 |
| 004 | vcenter-networks-empty | dc3-vc01 Networks tab empty | vcf_81 |
| 005 | portgroup-vm-mgmt-vlan16 | vm-mgmt port group, VLAN 16 (ephemeral) | vcf_86 |
| 006 | portgroup-esx-mgmt-vlan16 | esx-mgmt port group, VLAN 16 | vcf_87 |
| 007 | portgroup-vmotion-vlan17 | vMotion port group, VLAN 17 | vcf_85 |
| 008 | datastore-vmfs01 | VMFS01, VMFS 6, 10 TB | vcf_88 |
| 009 | datastore-vmfs01-detail | VMFS01 detail (near-dup) | vcf_89 |

## Act 2 — The underlay fix (Meraki: jumbo + L3 move to the switch stack)
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 010 | meraki-switches-online | 4 switches online (2× MS350 Core, 2× MS425 40GB stack) | vcf_100 |
| 011 | meraki-switch-stacks | Core + STACK 40GB stacks | vcf_101 |
| 012 | meraki-switch-stacks-closeup | (near-dup, cropped) | vcf_110 |
| 013 | meraki-mtu-9578-jumbo | Switch default MTU 9578 (jumbo) | vcf_102 |
| 014 | meraki-ports-ucs-fi-trunks | UCS FI-A/FI-B 40GB aggregate trunks | vcf_99 |
| 015 | mx-deployment-mode-routed | MX deployment mode = Routed | vcf_109 |
| 016 | mx-vlan-svi-list | MX VLAN/SVI list (NSX32/42/44/46…) | vcf_108 |
| 017 | mx-no-static-routes-yet | MX Addressing & VLANs — no static routes yet | vcf_107 |
| 018 | mx-dhcp-vlan44-reserved | MX DHCP VLAN 44, reserved .2–.14 | vcf_104 |
| 019 | mx-dhcp-vlan42-reserved | MX DHCP VLAN 42, reserved .2–.15 | vcf_105 |
| 020 | mx-dhcp-vlan42-pre-reservation | VLAN 42 before reservation (near-dup) | vcf_106 |
| 021 | mx-dhcp-reserved-vlan42-44 | MX DHCP reserved ranges VLAN 42 + 44 | vcf_98 |
| 022 | mx-static-route-add-modal | MX static route NSX-VPC-External → .44.11 (modal) | vcf_97 |
| 023 | mx-static-route-created | MX static route created → .44.11 | vcf_96 |
| 024 | switch-nav-routing-dhcp | Switching menu → Routing & DHCP | vcf_116 |
| 025 | switch-routing-empty | Switch Routing & DHCP empty | vcf_103 |
| 026 | switch-routing-empty-b | (near-dup) | vcf_112 |
| 027 | switch-static-routes-empty | Switch static routes empty | vcf_115 |
| 028 | switch-static-route-editor-empty | Empty static-route editor | vcf_111 |
| 029 | switch-static-route-editor-empty-b | (near-dup) | vcf_114 |
| 030 | switch-static-route-filled | Switch static route 10.103.50.0/24 → .44.11 | vcf_113 |
| 031 | switch-svi-transit-vlan99 | Creating transit VLAN 99 SVI (10.103.99.0/30) | vcf_94 |
| 032 | switch-svi-vlan42-defaultgateway-error | "first L3 interface needs defaultGateway" error | vcf_95 |
| 033 | switch-two-svis-99-42 | Two SVIs present (99, 42) | vcf_93 |
| 034 | switch-vlan32-dhcp-server | VLAN 32 host-TEP DHCP server config | vcf_92 |
| 035 | switch-svi-created-banner | "Interface has been created" banner | vcf_91 |
| 036 | switch-three-svis-jumbo-island | Final 3 SVIs on STACK 40GB (99/42/32) — jumbo island | vcf_90 |

## Act 3 — Pre-create NSX IP address blocks
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 037 | nsx-ipblock-external-edit | Editing external block 10.103.50.0/24 (External) | vcf_49 |
| 038 | nsx-ipblock-external-created | External block created | vcf_48 |
| 039 | nsx-ipblock-private-tgw-edit | Editing private TGW /16 block | vcf_46 |
| 040 | nsx-ipblocks-all-created | Day0 + external + private-tgw all present | vcf_45 |

## Act 4 — The spine wizard (Setup Network Connectivity)
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 041 | wizard-transit-gateways-start | Transit Gateways "Let's Get Started" (S01) | vcf_80 |
| 042 | wizard-tgw-connectivity-span | TGW Connectivity, Span dropdown (S02) | vcf_78 |
| 043 | wizard-centralized-connection | Centralized Connection selected (S02) | vcf_79 |
| 044 | wizard-prerequisites-unchecked | Prerequisites modal, unchecked (S03) | vcf_77 |
| 045 | wizard-prerequisites-checked | Prerequisites all checked (S03) | vcf_76 |
| 046 | wizard-prerequisites-checked-b | (near-dup) | vcf_75 |
| 047 | wizard-edge-cluster-empty | Edge Cluster step, no nodes (S04) | vcf_74 |
| 048 | addnode1-mgmt-cidr-required | Add Node — Management CIDR required error | vcf_73 |
| 049 | addnode1-portgroup-dropdown | Port Group dropdown (esx-mgmt/vmotion/vm-mgmt) | vcf_72 |
| 050 | addnode1-pg-esx-mgmt | Default pg-esx-mgmt selected | vcf_71 |
| 051 | addnode1-pg-esx-mgmt-b | (near-dup) | vcf_70 |
| 052 | addnode1-host-overlay-checked | Mgmt settings, host-overlay box checked | vcf_69 |
| 053 | addnode1-uplinks-host-overlay | Uplinks "use host overlay" highlighted | vcf_68 |
| 054 | addnode1-resources-vmfs01 | Resources pool, VMFS01 datastore | vcf_66 |
| 055 | addnode1-tep-ip-pool-select | Selecting TEP IP pool humbledgeeks-cl01-tep01 (S06) | vcf_67 |
| 056 | addnode1-error-15000-not-enough-ip | "[Fabric] Not enough IP address… Error code 15000" | vcf_64 |
| 057 | nsx-tep-pool-two-ranges | TEP pool: .2–.9 + .10–.100 (stale) | vcf_63 |
| 058 | nsx-tep-pool-trimmed | TEP pool trimmed to .2–.16 | vcf_62 |
| 059 | addnode1-runcheck-4-supported-hosts | Run Check green "4 SUPPORTED HOSTS" (S07) | vcf_65 |
| 060 | wizard-edge-cluster-node1-added | Edge cluster, 1 node added (S04 result) | vcf_61 |
| 061 | addnode2-placement-vmfs01 | Add Node edge02: mgmt .139, VMFS01 | vcf_60 |
| 062 | addnode2-tep-runcheck | Edge02 TEP VLAN 32 + Run Check | vcf_59 |
| 063 | wizard-edge-cluster-both-nodes | Edge cluster "2 Nodes" (S08) | vcf_58 |
| 064 | wdc-bgp-on-gateway-blank | Workload Domain Connectivity, BGP On, name blank | vcf_57 |
| 065 | wdc-bgp-on-local-asn | BGP On exposes Local ASN field | vcf_56 |
| 066 | wdc-bgp-off-top | BGP toggled Off, T0 dc3-mgmt-t0-gw01 (S10) | vcf_52 |
| 067 | wdc-edge1-uplink-44-11 | Edge01 uplink VLAN 44, 10.103.44.11/24 (S11) | vcf_55 |
| 068 | wdc-edge1-second-uplink-optional | Edge01 second uplink left blank | vcf_54 |
| 069 | wdc-edge2-uplink-44-12 | Edge02 uplink VLAN 44, 10.103.44.12/24 (S11) | vcf_53 |
| 070 | wdc-vpc-network-config-highlight | VPC Network Configuration section highlighted | vcf_51 |
| 071 | wdc-external-block-no-items-found | Typing CIDR → "No items Found" (S12) | vcf_50 |
| 072 | wdc-day0-private-block | Day0 Private Tgw block (the wrong default) | vcf_47 |
| 073 | wdc-private-tgw-block-dropdown | Private TGW block dropdown (Day0 vs custom /16) (S13) | vcf_44 |
| 074 | wdc-complete-t0-both-blocks | WDC complete: T0 + both VPC blocks (S10/12/13) | vcf_41 |
| 075 | wdc-complete-fullview | (full-chrome view, dup) | vcf_42 |
| 076 | wdc-complete-fullview-b | (dup) | vcf_43 |
| 077 | review-and-deploy-summary | Review & Deploy summary (S14) | vcf_39 |
| 078 | review-deploy-enabled | Review, DEPLOY enabled | vcf_40 |
| 079 | deploy-submitted-banner | "Request… successfully submitted" (S15) | vcf_38 |
| 080 | deploy-ovf-progress | Deploy OVF template ~32–34% (S16) | vcf_37 |
| 081 | edge-cluster-inprogress | Edge cluster In Progress, connectivity pending | vcf_36 |
| 082 | edge-cluster-success-connectivity-pending | Success but "2 Not Available" | vcf_35 |
| 083 | edge-cluster-2-up-success | Edge cluster 2 Up / Success (S16 done) | vcf_34 |

## Act 5 — Post-deploy on NSX Manager (static route, HA VIP, SNAT)
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 084 | t0-list-success | Tier-0 dc3-mgmt-t0-gw01 Success | vcf_24 |
| 085 | t0-edit-static-routes-set | T0 edit, Static Routes "Set" highlighted | vcf_32 |
| 086 | static-routes-empty | Static Routes modal empty | vcf_31 |
| 087 | set-static-routes-browser | Set Static Routes (browser view; low-res) | vcf_30 |
| 088 | add-route-default-route-to-mx | Add route default-route-to-mx, 0.0.0.0/0 | vcf_27 |
| 089 | next-hop-44-1-entry | Next hop 10.103.44.1, AD 1 entry | vcf_29 |
| 090 | next-hop-44-1-set | Next hop set | vcf_28 |
| 091 | route-added-uninitialized | Route added, status Uninitialized | vcf_26 |
| 092 | route-success | Route status Success | vcf_25 |
| 093 | t0-updated-1-static-route | T0 updated, 1 static route | vcf_18 |
| 094 | t0-edit-ha-vip-set | T0 edit, HA VIP "Set" highlighted | vcf_23 |
| 095 | ha-vip-empty | HA VIP config empty | vcf_22 |
| 096 | ha-vip-editing-unsaved | HA VIP editing, unsaved | vcf_19 |
| 097 | ha-vip-entry-44-10 | HA VIP 10.103.44.10/24, both uplinks, enabled | vcf_21 |
| 098 | ha-vip-set-44-10 | HA VIP set | vcf_20 |
| 099 | t0-ha-active-standby-vip | T0 Active/Standby, 1 HA VIP | vcf_16 |
| 100 | t0-bgp-settings | T0 BGP panel (NOTE: shows BGP On — see flag) | vcf_17 |
| 101 | extconn-form-snat-off | External connection form, SNAT off | vcf_13 |
| 102 | extconn-snat-off | SNAT off | vcf_12 |
| 103 | extconn-snat-on-no-blocks | SNAT On, "No Items Found" for blocks | vcf_11 |
| 104 | extconn-snat-on-external-block | SNAT On + external block set | vcf_10 |
| 105 | extconn-snat-configured | SNAT fully configured (external + SNAT block) | vcf_9 |
| 106 | extconn-updated-converging | External connection updated, converging | vcf_8 |

## Act 6 — MX route flip to the VIP
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 107 | mx-route-flip-to-vip | MX static route next hop → 10.103.44.10 (VIP) | vcf_7 |

## Act 7 — Validation / the payoff
| # | New file | Shows | Was |
|---|----------|-------|-----|
| 108 | extconn-inprogress | External connection In Progress | vcf_5 |
| 109 | extconn-inprogress-browser | (near-dup, windowed) | vcf_6 |
| 110 | tgw-up-linked-success | Default TGW up, linked to external connection | vcf_14 |
| 111 | extconn-success | External connection Success | vcf_15 |
| 112 | extconn-success-b | (near-dup) | vcf_4 |
| 113 | nsx-overview-after | NSX Overview "after": 1 Tier-0, 1 External, 2 Segments | vcf_3 |
| 114 | hosts-4-prepared | 4 hosts prepared for NSX (humbledgeeks-cl01) | vcf_2 |
| 115 | edge-cluster-tunnels-up | Edge cluster 2 Up, Tunnels ↑4 each | vcf_1 |
| 116 | t0-routing-table-menu | Tier-0 row menu (routing-table downloads) | vcf_33 |

## Unused
| # | New file | Shows | Was |
|---|----------|-------|-----|
| — | zzz-blank-unused | Blank capture (~5 KB) — drop from post | vcf_82 |

---

### Notes / flags
- **BGP discrepancy:** the wizard screens (066, 074, 077) show **BGP Off** (the
  static-routing design the runbook describes). The post-deploy NSX Manager T0
  panels (099, 100) show **BGP On / AS 65000**. Worth confirming which is the
  final intended state before publishing; captions follow the runbook (static).
- **No literal screenshot** exists of (a) the *empty* Supervisor VPC-profile
  dropdown — the "wall" is conveyed by 001/002 — or (b) the *populated* dropdown
  payoff (S22), or (c) S23 reachability. The set still paints the full workflow.
- Several near-duplicates kept and labeled `-b` so nothing is lost; the blog uses
  one of each.
