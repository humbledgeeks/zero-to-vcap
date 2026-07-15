# S23 Remediation — Finish North-South Inbound to the NSX VPC (Supervisor External API)

*dc3 / humbledgeeks.com — completing the one deferred step (S23) from `runbook.md` so the
NSX-VPC Supervisor's external API endpoint (and, after it, VKS guest clusters + LoadBalancer
services like Kubedoom) become reachable on TCP.*

> **This is the fix that unblocks the "Zero to VCAP" VKS / Doom post.** The whole VKS build
> is gated on this. Once `Test-NetConnection 10.103.50.5 -Port 6443` returns
> `TcpTestSucceeded : True`, the rest of the deployment is ~20 minutes.

---

## Problem statement (one paragraph — also the Broadcom case summary)

On a VCF 9.1 deployment with an **NSX-VPC-networked vSphere Supervisor**
(`dc3-mgmt-supervisor`, registered to workload-domain vCenter `dc3-vc02`), the Supervisor's
**published API / CLI-tools endpoint `https://10.103.50.5/`** is **unreachable on TCP 443
and 6443 from every external network tested** — both the admin jumphost
(`10.103.253.0/24`) and a **management host (`10.103.16.151`, VLAN 16)** get
`TcpTestSucceeded : False` while **ICMP to `10.103.50.5` succeeds**. The Supervisor itself
is healthy (vCenter manages it over its internal management interfaces). In NSX:
**"No External IPs found"** in any VPC, **no load-balancer virtual server** exists for the
API VIP (all 67 LB virtual servers are internal `10.96.0.x` ClusterIP services), and the
Supervisor's **API Server DNS Name is unset**. The control plane sits on a **Private VPC
subnet**, so `10.103.50.5` requires an inbound NAT / external-IP binding to be reachable —
and that binding never formed.

**Root cause:** the NSX-spine **north-south reachability step (S23 in `runbook.md`) was
deferred** ("Final acceptance … needs a tenant workload … record after Supervisor
deploys") and never completed. The Supervisor was enabled before inbound north-south
worked, so its external API exposure never converged. Outbound SNAT (S19) is configured;
the **inbound** path was never finished.

**Sharpest clue (for Broadcom):** the Supervisor **control plane lives on the management
subnet `10.103.16.65–69`** (the wizard's "Use ESXi Management VMK settings" option), while
the **API endpoint VIP `10.103.50.5` is in the NSX-VPC external block**. The LB/NAT that
must bridge the in-VPC external VIP to the out-of-VPC management-subnet control plane on
`:6443` **does not exist** — no LB virtual server for `10.103.50.5`, no external-IP
binding. The namespace network operator is healthy (`SubnetSet` / `NetworkInfo` CRs report
`SuccessfulUpdate`, no errors), so this is a **silent** failure to create the API
front-end, not a controller error.

**Remediation attempt #1 (failed — record):** Set the **API Server DNS Name**
(`dc3-supervisor-api.humbledgeeks.com → 10.103.50.5`) to force a Supervisor network
reconfigure (Phase 3, Step 8). The reconfigure **completed** (Config Status → Running),
DNS resolves correctly, and an external IP was allocated (block usage 2.73% → 3.13%) — but
**TCP 443/6443 still fail and `External IPs` is still empty.** The gentle re-converge did
**not** create the API LB binding. → Escalate to Phase 3, Step 9 (deliberate reconcile,
Broadcom-validated).

---

## What's already healthy (do NOT rebuild these)

| Component | State | Evidence |
|---|---|---|
| Routing jumphost → VIP | ✅ | `tracert` completes: `10.103.253.1 → 10.103.44.10 → 10.103.50.0 → 10.103.50.5` |
| Meraki MX | ✅ not blocking | Static route `10.103.50.0/24 → 10.103.44.10`; L3 **outbound = default-Allow** |
| Tier-0 `dc3-mgmt-t0-gw01` | ✅ Success | Active/Standby, HA VIP `10.103.44.10`, edge cluster bound, BGP/OSPF off (static) |
| External Connection | ✅ Success | `Gateway-connection-dc3-mgmt-t0-gw01`, outbound SNAT on (S19) |
| Edge cluster | ✅ 2 Up | `dc3-mgmt-edge-cl01`, tunnels up (VLAN 32 collapsed TEP) |
| T0 Gateway Firewall | ✅ off | not enforced — not the blocker |
| VPC connectivity profile | ✅ exists | Default VPC Connectivity Profile (S22 payoff) |
| Supervisor health | ✅ Ready | K8s Ready, Node Health Healthy, internal `10.96.0.x` LBs all Success |

**The gap is exactly one thing:** inbound north-south delivery of TCP to the VPC's
external block, and the Supervisor's external-IP binding for `10.103.50.5`.

---

## Remediation — do this in a maintenance window, not before a live demo

### Phase 1 — Prove the spine northbound (fast, read-only)
1. **T0 uplinks Up:** NSX → Tier-0 `dc3-mgmt-t0-gw01` → Interfaces → both `External-interface44` (`10.103.44.11/.12`) **Up**.  *(Confirmed healthy.)*
2. **Edge → MX:** SSH active edge (`admin@10.103.16.138`) → `get logical-routers` → `vrf <t0-sr-id>` → `ping 10.103.44.1` (MX SVI). Must succeed.
3. **MX → VIP:** from any non-VPC host, `ping 10.103.44.10` (HA VIP). *(Already succeeds.)*

If Phase 1 passes (it should — everything's green), the spine is fine and the problem is purely **inbound exposure**, below.

### Phase 2 — Find why inbound TCP isn't delivered (read-only diagnosis)
4. **External block visibility:** NSX → IP Management → IP Address Blocks → `vpc-external-10.103.50.0-24` → confirm **Visibility = Public/External**.
5. **Route advertisement inbound:** NSX → VPC Connectivity → External Connections → `Gateway-connection-dc3-mgmt-t0-gw01` → confirm the external block is advertised **inbound** (not just used for outbound SNAT). On a static-routed T0, confirm **route re-distribution** includes the VPC/connected external routes.
6. **NAT / external IP for the API:** NSX → VPCs → (the Supervisor's `kube-system` VPC) → **NAT** and **External IPs**. Expected finding: **no DNAT / no external-IP binding** mapping `10.103.50.5 → <control-plane private IP>`. *(This is the smoking gun — "No External IPs found.")*
7. **DFW (last firewall, read-only):** NSX → Security → Distributed Firewall (3 policies) → check for a rule scoping the control-plane segment / `6443` to internal sources only. If present, it is **by-design** control-plane protection — the fix is supported external-access config, **not** editing the DFW.

### Phase 3 — Re-converge the Supervisor's external API exposure (the actual fix)
The inbound external-IP/DNAT for the API VIP is **created automatically by the Supervisor**
when its NSX-VPC networking is healthy. Because north-south was broken at enablement, it
never formed. To make it converge:

8. **Set the API Server DNS Name** (supported, low-risk): vSphere Client → Workload
   Management → `dc3-mgmt-supervisor` → Configure → **Network → API Server DNS Names → ADD**
   an FQDN that resolves to `10.103.50.5`. This can trigger (re)creation of the external API
   endpoint. Create the matching DNS A record first.
9. **If the binding still doesn't form**, the Supervisor's NSX-VPC networking needs to be
   reconciled/re-applied so it re-runs external-IP allocation now that north-south works.
   **⚠️ This is the VCF-managed Supervisor↔NSX-VPC integration — validate the exact procedure
   with Broadcom support before executing.** Do not hand-create the DNAT/external-IP in NSX
   directly: the NSX Manager is VCF-managed and a manual binding will be reconciled away
   and/or conflict. The paste-ready case summary is the "Problem statement" section above.

### Phase 4 — Validate, then build
10. From any management host:
    ```powershell
    Test-NetConnection 10.103.50.5 -Port 6443   # want TcpTestSucceeded : True
    Test-NetConnection 10.103.50.5 -Port 443
    ```
11. Browse `https://10.103.50.5/` → the **Kubernetes CLI Tools** page should load (cert warning expected).
12. `kubectl vsphere login --server=10.103.50.5 --vsphere-username allen@humbledgeeks.com --insecure-skip-tls-verify` → succeeds.
13. Resume the VKS / Kubedoom build (Steps 8–13 in `vcf-vks/vcf-vks-kubernetes-doom.md`).

---

## Acceptance criteria
- `Test-NetConnection 10.103.50.5 -Port 6443` → `TcpTestSucceeded : True` from a host on a management/admin VLAN.
- NSX → VPCs → External IPs shows a binding for the API VIP (and later, for the Kubedoom LoadBalancer).
- `kubectl vsphere login` succeeds and `kubectl get ns` lists `vks-doom`.

## The lesson (for the blog)
A networking step marked **"deferred — validate later"** is a time bomb. S23 looked
optional because everything *appeared* healthy (the Supervisor enabled, the dashboard was
green). It only detonated when the first real workload needed the inbound path. Finish your
north-south validation **before** you layer a Supervisor on top — or it finishes you, later,
in front of a sponsor.
