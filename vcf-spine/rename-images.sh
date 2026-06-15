#!/usr/bin/env bash
# Reorders the vcf-spine screenshots from reverse-capture order into true
# chronological workflow order, with descriptive (SEO-friendly) filenames.
# Safe: verifies every source exists and is referenced exactly once before moving.
set -euo pipefail

cd "$(dirname "$0")/images"

# new_name <- old_file   (chronological order, 001..117)
MAP=(
# ---- ACT 1: environment + the wall ----
"vcf91-wld-001-nsx-overview-before.jpg|vcf_117.jpg"
"vcf91-wld-002-transit-gateway-empty-shell.jpg|vcf_84.jpg"
"vcf91-wld-003-vpc-get-started.jpg|vcf_83.jpg"
"vcf91-wld-004-vcenter-networks-empty.jpg|vcf_81.jpg"
"vcf91-wld-005-portgroup-vm-mgmt-vlan16.jpg|vcf_86.jpg"
"vcf91-wld-006-portgroup-esx-mgmt-vlan16.jpg|vcf_87.jpg"
"vcf91-wld-007-portgroup-vmotion-vlan17.jpg|vcf_85.jpg"
"vcf91-wld-008-datastore-vmfs01.jpg|vcf_88.jpg"
"vcf91-wld-009-datastore-vmfs01-detail.jpg|vcf_89.jpg"
# ---- ACT 2: the underlay fix (Meraki) ----
"vcf91-wld-010-meraki-switches-online.jpg|vcf_100.jpg"
"vcf91-wld-011-meraki-switch-stacks.jpg|vcf_101.jpg"
"vcf91-wld-012-meraki-switch-stacks-closeup.jpg|vcf_110.jpg"
"vcf91-wld-013-meraki-mtu-9578-jumbo.jpg|vcf_102.jpg"
"vcf91-wld-014-meraki-ports-ucs-fi-trunks.jpg|vcf_99.jpg"
"vcf91-wld-015-mx-deployment-mode-routed.jpg|vcf_109.jpg"
"vcf91-wld-016-mx-vlan-svi-list.jpg|vcf_108.jpg"
"vcf91-wld-017-mx-no-static-routes-yet.jpg|vcf_107.jpg"
"vcf91-wld-018-mx-dhcp-vlan44-reserved.jpg|vcf_104.jpg"
"vcf91-wld-019-mx-dhcp-vlan42-reserved.jpg|vcf_105.jpg"
"vcf91-wld-020-mx-dhcp-vlan42-pre-reservation.jpg|vcf_106.jpg"
"vcf91-wld-021-mx-dhcp-reserved-vlan42-44.jpg|vcf_98.jpg"
"vcf91-wld-022-mx-static-route-add-modal.jpg|vcf_97.jpg"
"vcf91-wld-023-mx-static-route-created.jpg|vcf_96.jpg"
"vcf91-wld-024-switch-nav-routing-dhcp.jpg|vcf_116.jpg"
"vcf91-wld-025-switch-routing-empty.jpg|vcf_103.jpg"
"vcf91-wld-026-switch-routing-empty-b.jpg|vcf_112.jpg"
"vcf91-wld-027-switch-static-routes-empty.jpg|vcf_115.jpg"
"vcf91-wld-028-switch-static-route-editor-empty.jpg|vcf_111.jpg"
"vcf91-wld-029-switch-static-route-editor-empty-b.jpg|vcf_114.jpg"
"vcf91-wld-030-switch-static-route-filled.jpg|vcf_113.jpg"
"vcf91-wld-031-switch-svi-transit-vlan99.jpg|vcf_94.jpg"
"vcf91-wld-032-switch-svi-vlan42-defaultgateway-error.jpg|vcf_95.jpg"
"vcf91-wld-033-switch-two-svis-99-42.jpg|vcf_93.jpg"
"vcf91-wld-034-switch-vlan32-dhcp-server.jpg|vcf_92.jpg"
"vcf91-wld-035-switch-svi-created-banner.jpg|vcf_91.jpg"
"vcf91-wld-036-switch-three-svis-jumbo-island.jpg|vcf_90.jpg"
# ---- ACT 3: pre-create NSX IP address blocks ----
"vcf91-wld-037-nsx-ipblock-external-edit.jpg|vcf_49.jpg"
"vcf91-wld-038-nsx-ipblock-external-created.jpg|vcf_48.jpg"
"vcf91-wld-039-nsx-ipblock-private-tgw-edit.jpg|vcf_46.jpg"
"vcf91-wld-040-nsx-ipblocks-all-created.jpg|vcf_45.jpg"
# ---- ACT 4: the spine wizard (Setup Network Connectivity) ----
"vcf91-wld-041-wizard-transit-gateways-start.jpg|vcf_80.jpg"
"vcf91-wld-042-wizard-tgw-connectivity-span.jpg|vcf_78.jpg"
"vcf91-wld-043-wizard-centralized-connection.jpg|vcf_79.jpg"
"vcf91-wld-044-wizard-prerequisites-unchecked.jpg|vcf_77.jpg"
"vcf91-wld-045-wizard-prerequisites-checked.jpg|vcf_76.jpg"
"vcf91-wld-046-wizard-prerequisites-checked-b.jpg|vcf_75.jpg"
"vcf91-wld-047-wizard-edge-cluster-empty.jpg|vcf_74.jpg"
"vcf91-wld-048-addnode1-mgmt-cidr-required.jpg|vcf_73.jpg"
"vcf91-wld-049-addnode1-portgroup-dropdown.jpg|vcf_72.jpg"
"vcf91-wld-050-addnode1-pg-esx-mgmt.jpg|vcf_71.jpg"
"vcf91-wld-051-addnode1-pg-esx-mgmt-b.jpg|vcf_70.jpg"
"vcf91-wld-052-addnode1-host-overlay-checked.jpg|vcf_69.jpg"
"vcf91-wld-053-addnode1-uplinks-host-overlay.jpg|vcf_68.jpg"
"vcf91-wld-054-addnode1-resources-vmfs01.jpg|vcf_66.jpg"
"vcf91-wld-055-addnode1-tep-ip-pool-select.jpg|vcf_67.jpg"
"vcf91-wld-056-addnode1-error-15000-not-enough-ip.jpg|vcf_64.jpg"
"vcf91-wld-057-nsx-tep-pool-two-ranges.jpg|vcf_63.jpg"
"vcf91-wld-058-nsx-tep-pool-trimmed.jpg|vcf_62.jpg"
"vcf91-wld-059-addnode1-runcheck-4-supported-hosts.jpg|vcf_65.jpg"
"vcf91-wld-060-wizard-edge-cluster-node1-added.jpg|vcf_61.jpg"
"vcf91-wld-061-addnode2-placement-vmfs01.jpg|vcf_60.jpg"
"vcf91-wld-062-addnode2-tep-runcheck.jpg|vcf_59.jpg"
"vcf91-wld-063-wizard-edge-cluster-both-nodes.jpg|vcf_58.jpg"
"vcf91-wld-064-wdc-bgp-on-gateway-blank.jpg|vcf_57.jpg"
"vcf91-wld-065-wdc-bgp-on-local-asn.jpg|vcf_56.jpg"
"vcf91-wld-066-wdc-bgp-off-top.jpg|vcf_52.jpg"
"vcf91-wld-067-wdc-edge1-uplink-44-11.jpg|vcf_55.jpg"
"vcf91-wld-068-wdc-edge1-second-uplink-optional.jpg|vcf_54.jpg"
"vcf91-wld-069-wdc-edge2-uplink-44-12.jpg|vcf_53.jpg"
"vcf91-wld-070-wdc-vpc-network-config-highlight.jpg|vcf_51.jpg"
"vcf91-wld-071-wdc-external-block-no-items-found.jpg|vcf_50.jpg"
"vcf91-wld-072-wdc-day0-private-block.jpg|vcf_47.jpg"
"vcf91-wld-073-wdc-private-tgw-block-dropdown.jpg|vcf_44.jpg"
"vcf91-wld-074-wdc-complete-t0-both-blocks.jpg|vcf_41.jpg"
"vcf91-wld-075-wdc-complete-fullview.jpg|vcf_42.jpg"
"vcf91-wld-076-wdc-complete-fullview-b.jpg|vcf_43.jpg"
"vcf91-wld-077-review-and-deploy-summary.jpg|vcf_39.jpg"
"vcf91-wld-078-review-deploy-enabled.jpg|vcf_40.jpg"
"vcf91-wld-079-deploy-submitted-banner.jpg|vcf_38.jpg"
"vcf91-wld-080-deploy-ovf-progress.jpg|vcf_37.jpg"
"vcf91-wld-081-edge-cluster-inprogress.jpg|vcf_36.jpg"
"vcf91-wld-082-edge-cluster-success-connectivity-pending.jpg|vcf_35.jpg"
"vcf91-wld-083-edge-cluster-2-up-success.jpg|vcf_34.jpg"
# ---- ACT 5: post-deploy on NSX Manager ----
"vcf91-wld-084-t0-list-success.jpg|vcf_24.jpg"
"vcf91-wld-085-t0-edit-static-routes-set.jpg|vcf_32.jpg"
"vcf91-wld-086-static-routes-empty.jpg|vcf_31.jpg"
"vcf91-wld-087-set-static-routes-browser.jpg|vcf_30.jpg"
"vcf91-wld-088-add-route-default-route-to-mx.jpg|vcf_27.jpg"
"vcf91-wld-089-next-hop-44-1-entry.jpg|vcf_29.jpg"
"vcf91-wld-090-next-hop-44-1-set.jpg|vcf_28.jpg"
"vcf91-wld-091-route-added-uninitialized.jpg|vcf_26.jpg"
"vcf91-wld-092-route-success.jpg|vcf_25.jpg"
"vcf91-wld-093-t0-updated-1-static-route.jpg|vcf_18.jpg"
"vcf91-wld-094-t0-edit-ha-vip-set.jpg|vcf_23.jpg"
"vcf91-wld-095-ha-vip-empty.jpg|vcf_22.jpg"
"vcf91-wld-096-ha-vip-editing-unsaved.jpg|vcf_19.jpg"
"vcf91-wld-097-ha-vip-entry-44-10.jpg|vcf_21.jpg"
"vcf91-wld-098-ha-vip-set-44-10.jpg|vcf_20.jpg"
"vcf91-wld-099-t0-ha-active-standby-vip.jpg|vcf_16.jpg"
"vcf91-wld-100-t0-bgp-settings.jpg|vcf_17.jpg"
"vcf91-wld-101-extconn-form-snat-off.jpg|vcf_13.jpg"
"vcf91-wld-102-extconn-snat-off.jpg|vcf_12.jpg"
"vcf91-wld-103-extconn-snat-on-no-blocks.jpg|vcf_11.jpg"
"vcf91-wld-104-extconn-snat-on-external-block.jpg|vcf_10.jpg"
"vcf91-wld-105-extconn-snat-configured.jpg|vcf_9.jpg"
"vcf91-wld-106-extconn-updated-converging.jpg|vcf_8.jpg"
# ---- ACT 6: MX route flip to the VIP ----
"vcf91-wld-107-mx-route-flip-to-vip.jpg|vcf_7.jpg"
# ---- ACT 7: validation / the payoff ----
"vcf91-wld-108-extconn-inprogress.jpg|vcf_5.jpg"
"vcf91-wld-109-extconn-inprogress-browser.jpg|vcf_6.jpg"
"vcf91-wld-110-tgw-up-linked-success.jpg|vcf_14.jpg"
"vcf91-wld-111-extconn-success.jpg|vcf_15.jpg"
"vcf91-wld-112-extconn-success-b.jpg|vcf_4.jpg"
"vcf91-wld-113-nsx-overview-after.jpg|vcf_3.jpg"
"vcf91-wld-114-hosts-4-prepared.jpg|vcf_2.jpg"
"vcf91-wld-115-edge-cluster-tunnels-up.jpg|vcf_1.jpg"
"vcf91-wld-116-t0-routing-table-menu.jpg|vcf_33.jpg"
# ---- unused / blank capture (kept, sorts last) ----
"vcf91-wld-zzz-blank-unused.jpg|vcf_82.jpg"
)

# --- verify before moving ---
echo "Verifying ${#MAP[@]} mappings..."
[ "${#MAP[@]}" -eq 117 ] || { echo "ERROR: expected 117 entries, got ${#MAP[@]}"; exit 1; }

declare -A seen
for pair in "${MAP[@]}"; do
  old="${pair#*|}"
  [ -f "$old" ] || { echo "ERROR: source missing: $old"; exit 1; }
  [ -z "${seen[$old]:-}" ] || { echo "ERROR: source listed twice: $old"; exit 1; }
  seen[$old]=1
done
echo "All 117 sources present and unique. Renaming..."

for pair in "${MAP[@]}"; do
  new="${pair%%|*}"
  old="${pair#*|}"
  mv -n "$old" "$new"
done

echo "Done. Remaining un-renamed vcf_*.jpg (should be none):"
ls vcf_*.jpg 2>/dev/null || echo "  (none)"
echo "New file count: $(ls vcf91-wld-*.jpg | wc -l | tr -d ' ')"
