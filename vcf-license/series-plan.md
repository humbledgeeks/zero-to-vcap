# VCF 9.1 FlexPod — Blog Series & Sponsor Demo Plan

Environment: FlexPod (Cisco UCS + NetApp ASA30), VCF 9.1, management domain +
workload domain (Supervisor enabled). Driving event: lab demo for Broadcom
Knight sponsor. Differentiator vs. generic VCF blogs: the FlexPod / NetApp angle.

---

## Order of next steps

1. **Identity & RBAC** — tie VCF to Humbledgeeks AD
2. **NetApp ONTAP tools / VASA** — deploy in the management domain (vVols)
3. **Supervisor / VKS workloads** — Doom pod (icebreaker) + a real stateful app on NetApp
4. **Cross-vCenter migration** — move a VM from prod (8.0U3) into the workload domain
5. **Backup / Restore** — VCF-native + NetApp SnapCenter (Veeam stays the prod tool)
6. **Lifecycle Management** — depot registration + apply an update
- **Back burner:** Certificates (stand up AD CS first, then revisit)

---

## Phase 1 — Identity & RBAC (VCF ↔ Humbledgeeks AD)

- **Goal:** External identity provider for SSO + role-based access, backed by AD over LDAPS.
- **Steps:** configure the identity source (AD/LDAPS), map AD groups to VCF/vCenter roles, validate least-privilege login, document the role model.
- **Sponsor value:** enterprise-readiness signal; proves it's not a single-admin lab.
- **Prereqs:** AD reachable from the mgmt domain; LDAPS (a cert on the DC) — if you only have LDAP today, note it; LDAPS is the right answer.
- **Verify:** supported identity-provider options in VCF 9.1 (Workspace ONE / Entra / LDAP-AD) before committing the post.

## Phase 2 — NetApp ONTAP tools / VASA (vVols)

- **Goal:** Deploy ONTAP tools for VMware vSphere (carries the VASA Provider) and present a vVols datastore.
- **Placement:** deploy the **OVA as a VM in the management domain**; register VASA to the mgmt-domain vCenter.
- **Note on "container":** ONTAP tools 10.x is container-based internally but ships as an OVA — from your side it is a VM. That's likely what you read.
- **Sponsor value:** per-VM storage policy (SPBM), QoS, ONTAP snapshots — storage depth on the FlexPod.
- **Verify:** ONTAP tools 10.x support for vSphere 9 in the **NetApp IMT** before deploying.

## Phase 3 — Supervisor / VKS workloads (the demo)

- **Goal:** Show modern apps on the workload domain + NetApp serving container storage.
- **3a — Doom pod (icebreaker):** deploy in a VKS guest cluster. Gets the smile; not the whole act.
- **3b — Real stateful app (substance):** deploy a multi-container app whose persistent volumes land on NetApp via **Trident (CSI)**. Candidate: **Immich** (see notes) or a simpler Postgres/Grafana stack.
- **Sponsor value:** "I run modern apps AND my FlexPod storage provisions for them dynamically."
- **Prereqs:** Supervisor enabled (done), a vSphere Namespace, a VKS cluster, Trident installed in the guest cluster pointed at ONTAP.
- **Verify:** Trident release support for VKS / vSphere 9 in the NetApp IMT.

## Phase 4 — Cross-vCenter migration (use case)

- **Goal:** Advanced Cross vCenter vMotion of a VM from the production 8.0U3 environment into the VCF 9.1 workload domain (cross-version, shared-nothing).
- **Sponsor value:** real migration story — "bring existing workloads onto VCF."
- **CAUTION — do not migrate your only/primary AD domain controller live to a sponsor.** DC vMotion is generally supported on modern Windows (VM-GenerationID), but avoid snapshot reverts/clones and don't risk the optics. Use a **throwaway VM or a secondary/test DC** for the demo.
- **Prereqs:** destination network so the VM keeps connectivity (same subnet via NSX segment or VLAN-backed portgroup); compatible EVC.
- **Verify:** 8.0U3 → 9.1 cross-vCenter vMotion interop (source/target version support) before you demo.

## Phase 5 — Backup / Restore

- **Goal:** Showcase platform + FlexPod data protection.
- **Show:** VCF-native backup/restore (mgmt components to SFTP, file-based vCenter backup) **+ NetApp SnapCenter Plug-in for VMware vSphere**.
- **Mention:** Veeam is the production tool — name it, don't lead with it for a Broadcom sponsor.

## Phase 6 — Lifecycle Management

- **Goal:** Configure updates and apply one.
- **Steps:** register the software depot (Broadcom token / Software Depot Registration), pull an update, apply through VCF Operations.
- **Sponsor value:** operational maturity; pairs with the licensing post.

---

## Demo workloads menu (VMs and containers)

**VMs:**
- Throwaway Linux/Windows jump box (migration target / general testing)
- Secondary/test domain controller (safe AD migration demo)
- NetApp SnapCenter VMware plug-in appliance (Phase 5)

**Containers (VKS, with Trident-backed PVs where stateful):**
- Doom pod — icebreaker
- Immich — your real photo app; stateful, NetApp-backed, optional GPU (see notes)
- Postgres or MySQL with a Trident PVC — clean storage story
- Prometheus + Grafana — observability; exercises ReadWriteMany volumes
- A web app behind a LoadBalancer service — exercises NSX/AVN load balancing
- (Only if GPU present) a small inference app (e.g., Ollama) — ties the Private AI license

---

## Open items to verify before demoing

- NetApp IMT: ONTAP tools 10.x and Trident vs. vSphere 9 / VCF 9.1
- VCF 9.1 supported identity providers
- Cross-vCenter vMotion interop: 8.0U3 source → 9.1 target
- GPU availability in the FlexPod (gates any Private AI / ML demo)
