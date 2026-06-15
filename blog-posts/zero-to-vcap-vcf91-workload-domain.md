# Zero to VCAP: Building a VCF 9.1 Workload Domain, Screen by Screen

In the [last post](https://humbledgeeks.com/) <!-- TODO: swap in Part 1 URL once it's live --> I stood up a full **VMware Cloud Foundation 9.1 management domain** — vCenter, NSX, SDDC Manager, VCF Operations, and VCF Automation — on four Cisco UCS B200 blades. That domain is the foundation everything else hangs off of, but you don't run real workloads on it. The management plane is for managing the fleet; tenant VMs and clusters live in a **workload domain**.

So this post does exactly what I promised at the end of Part 1: I take the **remaining four B200 blades** in the same UCS 5108 chassis and turn them into a **VI (Virtual Infrastructure) workload domain** — a second vCenter, a new vSphere cluster, NSX networking, and VMFS-on-FC storage off the same NetApp ASA A30. I'd already started commissioning the hosts when I sat down to write this, and as always I grabbed a screenshot at every screen so you can follow along.

Same warning as last time: **this is a long one.** I'd rather over-document than leave you guessing at a screen. Grab a coffee.

## Management Domain vs. Workload Domain — and Why It Matters

If you're coming from classic vSphere, the VCF separation of "management domain" and "workload domain" is one of the first concepts worth getting straight — and it shows up on the VCAP-VCF blueprint.

- The **management domain** is deployed first (that was Part 1). It runs the VCF management plane itself: SDDC Manager, the first vCenter, an NSX instance, VCF Operations, and VCF Automation. It manages the fleet — you generally don't put production workloads on it.
- A **VI workload domain** is where your actual workloads live. Each VI workload domain gets **its own vCenter**, **its own vSphere cluster(s)**, and is attached to an **NSX instance** — either a brand-new one or an existing one you share. SDDC Manager provisions and lifecycle-manages all of it for you.

The payoff is operational separation with a single control plane: SDDC Manager patches, scales, and inventories every domain, but a problem (or a maintenance window) in a workload domain doesn't touch the management plane.

<!-- screenshot (optional): SDDC Manager inventory showing the management domain before we add the WD -->

## My Design Choices for This Workload Domain

Before the wizard, here's how I decided to build this WD — and why. Calling these out up front because the choices change which screens you see.

| Decision | What I chose | Why |
|---|---|---|
| **Principal storage** | VMFS on Fibre Channel (NetApp ASA A30) | Matches the management domain. My B200 blades are SAN-boot/diskless, so vSAN isn't on the table — the ASA A30 already serves the chassis over FC. |
| **NSX** | **Share the management domain's existing NSX instance** | Resource saver in the lab. Deploying a second NSX Manager cluster is a lot of appliances; sharing keeps me inside my host budget. |
| **Licensing** | Stay on the 90-day evaluation | I'll license the whole environment in the next post. For now the eval covers it. |
| **Hosts** | The 4 remaining B200 blades in the chassis | Finishes out the chassis — 4 for management, 4 for workloads. |

> **Gotcha:** Sharing an NSX instance is the right call for a lab, but in production it's a real tradeoff. A shared NSX instance means the management and workload domains share that networking fault domain and lifecycle. If you need hard isolation between the management plane and tenant networking, deploy a **dedicated** NSX instance for the workload domain instead. I'll point out the exact screen where you choose.

> **Tip:** Even though we're *sharing* NSX, a VI workload domain **always gets its own vCenter**. That surprises people who assume "shared NSX" means "shared everything." You'll still define a new vCenter (mine is `dc3-vc02`) joined to the same SSO domain as `dc3-vc01`.

## Prerequisites — What I Did Before Touching SDDC Manager

A workload domain build only goes smoothly if the hosts and fabric are ready *before* you commission anything. Here's my pre-flight checklist for the four new blades:

- [ ] **ESXi installed, hardened, and certificates regenerated** on all four hosts so they match their final FQDNs. This is the exact same prep I documented in the [VCF 9.1 deployment post](https://humbledgeeks.com/) <!-- TODO: Part 1 URL --> — my PowerShell hardening and cert-regen scripts — so I won't re-walk it here.
- [ ] **DNS forward and reverse records** for all four hosts *and* the new vCenter (`dc3-vc02`), on `humbledgeeks.com` (`10.103.20.11` / `10.103.20.12`).
- [ ] **NTP** configured and reachable on every host — time sync is a validation check and a silent killer if it's off.
- [ ] **FC LUN zoned and presented from the NetApp ASA A30 to all four hosts.** This is the big one for VMFS-on-FC. The datastore validation in the WD wizard will fail if the LUN isn't visible to every host. This is the same UCS/NetApp FC zoning dance from my [FlexPod foundation post](https://humbledgeeks.com/automating-a-cisco-ucs-flexpod-with-netapp-asa-a30-on-broadcom-vcf/).
- [ ] **Network pool** for the workload domain (vMotion range on VLAN 17, `10.103.17.0/24`), so commissioning has IPs to hand out.

> **Tip:** If you only check one thing before commissioning, make it FC LUN visibility. "Host can't see the datastore" is the most common reason a VMFS-on-FC workload domain validation falls over, and it's entirely a fabric/array problem, not a VCF one.

<!-- screenshot (optional): NetApp/UCS showing the FC LUN mapped to the 4 new hosts -->

## Phase 1 — Commission the Hosts

Everything starts in **SDDC Manager**. Before a host can join a workload domain it has to be *commissioned* into the SDDC Manager inventory, where it lands as an **Unassigned Host** ready to be picked up by a domain.

<!-- screenshot: SDDC Manager → Hosts → Commission Hosts; the prerequisite checklist screen -->
<!-- DESCRIPTION TODO: the commission prerequisites checklist screen and what I confirmed -->

<!-- screenshot: Add host form — FQDN, Storage Type = VMFS on FC, Network Pool, credentials -->
<!-- DESCRIPTION TODO: adding the first host; call out Storage Type = VMFS on FC and the network pool selection -->

<!-- screenshot: thumbprint / validation of the hosts before commissioning -->
<!-- DESCRIPTION TODO: confirming SSH/SSL thumbprints and the validation run -->

<!-- screenshot: hosts successfully commissioned, now in Unassigned Hosts -->
<!-- DESCRIPTION TODO: all four hosts commissioned and sitting in Unassigned Hosts -->

> **Gotcha:** Pick the **storage type at commission time** to match how the host will be used — I selected **VMFS on FC** here. Commission with the wrong storage type and you'll be decommissioning and redoing it before the WD wizard will take the host.

## Phase 2 — Start the VI Workload Domain Wizard

With four hosts unassigned, I kick off the workload domain itself: **SDDC Manager → Workload Domains → + Workload Domain → VI**.

<!-- screenshot: Workload Domains page with the + Workload Domain → VI menu -->
<!-- DESCRIPTION TODO: launching the wizard and choosing VI -->

<!-- screenshot: storage selection step — VMFS on FC -->
<!-- DESCRIPTION TODO: selecting VMFS on FC as the principal storage for the WD -->

## Phase 3 — Name the Domain and Cluster

<!-- screenshot: name the workload domain + cluster -->
<!-- DESCRIPTION TODO: workload-domain name and cluster name; carry the dc3- naming convention -->

## Phase 4 — Compute: the New vCenter

A VI workload domain stands up its own vCenter, joined to the existing SSO domain so it shows up alongside `dc3-vc01` under one pane of glass.

<!-- screenshot: vCenter details — FQDN (dc3-vc02), IP, subnet/gateway, root password -->
<!-- DESCRIPTION TODO: defining dc3-vc02 — FQDN/IP/gateway and passwords; note same SSO domain -->

> **Tip:** Make sure `dc3-vc02`'s forward and reverse DNS records already resolve before this step — the wizard validates them and a missing PTR record will stop you here.

## Phase 5 — Networking and NSX (Sharing the Existing Instance)

This is the screen where I make the shared-NSX choice from earlier real: instead of deploying a new NSX Manager cluster, I attach this workload domain to the management domain's **existing** NSX instance.

<!-- screenshot: NSX step — choosing existing NSX instance vs. create new -->
<!-- DESCRIPTION TODO: selecting the existing NSX instance (the share-vs-new fork); this is where you'd pick "create new" for isolation -->

<!-- screenshot: overlay / TEP / transport VLAN configuration -->
<!-- DESCRIPTION TODO: Geneve/overlay TEP VLAN and transport settings for the new cluster's transport nodes -->

> **Gotcha:** This is the fork in the road. Choosing the existing instance here is what makes this a *shared-NSX* workload domain. If you want a dedicated networking fault domain, pick **Create new NSX instance** instead — and budget for the extra appliances.

## Phase 6 — Select the Hosts

<!-- screenshot: host selection — the 4 commissioned B200 blades -->
<!-- DESCRIPTION TODO: selecting the four unassigned hosts for the new cluster -->

## Phase 7 — vDS / Switch Configuration

<!-- screenshot: distributed switch + vmnic-to-uplink mapping -->
<!-- DESCRIPTION TODO: vDS configuration, vmnic→uplink mapping, NIOC / traffic profile choices -->

## Phase 8 — Licensing

I'm staying on the **90-day evaluation** for now, so this step is quick — but it's where you'd add and assign real VCF/vSphere/NSX keys if you have them.

<!-- screenshot: license selection step (eval) -->
<!-- DESCRIPTION TODO: the licensing step on eval; note the 90-day clock -->

> **Tip:** The evaluation clock started when I deployed the management domain in Part 1 — it doesn't reset per domain. Licensing the whole environment (and then proving updates apply cleanly) is exactly what the next post covers.

## Phase 9 — Object Names and Review

<!-- screenshot: object naming summary -->
<!-- DESCRIPTION TODO: the object-name review screen -->

<!-- screenshot: review / summary before validation -->
<!-- DESCRIPTION TODO: the full review summary of the WD spec -->

> **Tip:** Use **Download JSON Spec** here. It's your as-built record of the workload domain, and it's the fastest way to rebuild or script this domain later.

## Phase 10 — Validation

Same safety net as the management-domain deploy: SDDC Manager runs a pre-flight against the whole spec before it builds anything.

<!-- screenshot: validation in progress / checks list -->
<!-- DESCRIPTION TODO: the validation run — call out DNS, VMFS FC datastore, network, NSX, and capacity checks -->

<!-- screenshot: validation complete (and any warnings acknowledged) -->
<!-- DESCRIPTION TODO: validation green; note any capacity warnings I acknowledged in the lab -->

> **Gotcha:** If validation flags the **VMFS FC datastore** check, the LUN isn't visible to one or more hosts — back to the array/zoning, not the wizard. This is why FC LUN visibility was top of the prerequisites list.

## Phase 11 — Deploy: Watching the Workload Domain Come Up

<!-- screenshot: deployment in progress milestone tracker -->
<!-- DESCRIPTION TODO: the milestone tracker kicking off -->

<!-- screenshot: vCenter deployed / cluster configured -->
<!-- DESCRIPTION TODO: dc3-vc02 deployed, cluster created, hosts attaching -->

<!-- screenshot: NSX transport nodes configured on the new cluster -->
<!-- DESCRIPTION TODO: the shared NSX instance configuring transport nodes on the new hosts -->

<!-- screenshot: deployment complete / success -->
<!-- DESCRIPTION TODO: workload domain deployment complete -->

## The Payoff and What I Took Away

<!-- screenshot: SDDC Manager inventory now showing both domains -->
<!-- DESCRIPTION TODO: final state — management domain + new VI workload domain side by side in SDDC Manager -->

When it finishes, I've got a second vCenter (`dc3-vc02`) and a fresh four-host cluster in inventory, the shared NSX instance now managing the new cluster's transport nodes, and a VMFS-on-FC datastore mounted from the ASA A30 — all provisioned and lifecycle-owned by SDDC Manager. The chassis is now fully in service: four blades for management, four for workloads.

<!-- KEY TAKEAWAYS TODO: 3-4 honest lessons once the build is done — e.g. FC LUN visibility being the make-or-break prereq, shared-NSX resource savings vs. isolation tradeoff, and anything that bit me. -->

The lab lesson that bears repeating from Part 1: **the storage and fabric work happens before VCF ever sees it.** A workload domain build is mostly VCF orchestration once the FC LUN is presented and the hosts are commissioned correctly — get those right and the wizard does the heavy lifting.

## What's Next

This post added the capacity. Next in the Zero to VCAP series, I'm tackling the two things every eval deployment eventually has to face:

- **License the environment** — logging into VCF Operations and applying license keys across the fleet **before that 90-day evaluation clock runs out** (it started back in Part 1 and it does not reset per domain).
- **Prove that updates work** — running a lifecycle/patch cycle through SDDC Manager to confirm the fleet updates cleanly. Standing it up is one thing; keeping it patched is the part that actually matters in production.

Further out, I'll converge my existing vCenter 8.0 U3 lab into the fleet and deploy a real workload onto this new domain.

Follow along on [HumbledGeeks.com](https://humbledgeeks.com), or connect with me on LinkedIn if you're on the same journey. As always — built in the lab, mistakes and all.
