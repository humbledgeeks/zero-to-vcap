# SOURCE-NOTES: VCF 9.1 Lifecycle & Upgrades

Source of truth for the post. Technical content pasted from the working brief.
Treat every fact here as ground truth for the draft. If a screenshot contradicts
a claim here, the screenshot wins, but flag it before changing the prose.

---

## Post angle

Not a troubleshooting post. This is about how lifecycle management actually works
in VCF 9.1, and how much the model improved compared to the VCF 8.0 U3 / 5.x era.
Tone: a practitioner explaining a genuine architectural improvement, not a vendor
pitch.

Core thesis: in the old model you operated two separate lifecycle systems. In
VCF 9.1 there is one control plane, and the mental model is fleet versus instance.

Important nuance that must be in the post: the steady-state model is dramatically
simpler, but the transition to 9.1 is a real project with real prerequisites. Do
not write this as "click upgrade and go."

Companion piece: the VVF vCenter upgrade post (draft ID 2567), linked as
https://humbledgeeks.com/?p=2567 . Note where the VVF path differs from full VCF.

---

## The old model: VCF 8.0 U3 and 5.x

You operated two lifecycle systems side by side.

**SDDC Manager** owned core infrastructure lifecycle: itself, NSX, vCenter, and
ESXi hosts. You downloaded bundles into SDDC Manager, either from an online depot
with credentials or via offline bundle transfer for dark sites. Upgrades ran
sequentially per workload domain: management domain first, then VI workload
domains.

**VMware Aria Suite Lifecycle** (vRSLCM, later ASLCM) owned the management and
Aria stack: Aria Operations, Aria Automation, Identity Manager. Separate appliance,
its own UI, its own binary management, its own upgrade workflow. Aria Suite
Lifecycle was decoupled from SDDC Manager after VCF 4.4.1, so those upgrades were
entirely your problem to sequence.

Practical result: two consoles, two binary repositories, two sets of prechecks,
and an upgrade order you had to know and enforce yourself. Typical order was Aria
stack first through Aria Suite Lifecycle, then SDDC Manager, then NSX, then
vCenter, then ESXi.

Context worth mentioning: vSphere Lifecycle Manager baselines still existed in
this era. VCF 9.0 removed baseline support in favor of single image management,
along with Enhanced Linked Mode, Integrated Windows Authentication, Storage IO
Control, Host Profiles, and vVols.

---

## What VCF 9.1 changed

VCF 9.0 introduced a standalone Fleet Management Appliance and a separate VMware
Identity Broker appliance cluster. VCF 9.1 removed both as standalone appliances
and folded their function into a container cluster called **VCF Management
Services**.

Lifecycle is now delivered by two services running natively in that cluster:

- **Fleet Lifecycle** owns fleet-level management components: VCF Operations,
  Operations for Logs, Operations for Networks, VCF Automation, and the Identity
  Broker. This is the Aria Suite Lifecycle lineage, absorbed into the platform.
- **SDDC Lifecycle** owns instance-level core components: vCenter, NSX, ESXi
  hosts, vSAN. This is the SDDC Manager lineage.

Both are driven from the VCF Operations console under **Build > Lifecycle**. The
Software Depot also runs as a component in the same cluster, so binary management
is centralized rather than duplicated.

Note for readers: the SDDC Manager UI is being deprecated and will be removed in a
future release. After upgrading to 9.1, lifecycle activities are performed from
VCF Operations.

---

## The fleet versus instance model (the key concept)

Mental model that makes VCF 9.1 lifecycle click.

**Fleet-level components** are shared across every VCF instance. Fleet Lifecycle,
Salt RaaS, the Software Depot, and the license server are deployed once and serve
the whole fleet. When you add a second or third VCF instance, only VCF Services
Runtime, Salt master, and SDDC Lifecycle get deployed for it. The fleet components
are shared from the first instance.

**Instance-level components** are per VCF instance. vCenter, NSX, ESXi, vSAN, and
SDDC Lifecycle exist once per instance.

Governing rule for upgrade sequencing: upgrade the fleet-level management
components first, then the instance-level core components. Fleet gates instance,
never the reverse. Start with the VCF instance hosting the VCF Operations instance
that manages your fleet, then work outward to workload domains.

That single rule replaces most of the sequencing knowledge you used to carry in
your head for the two-tool model.

---

## Upgrading management components (walkthrough)

1. Log in to VCF Operations
2. Top navigation: Build
3. Left pane: Lifecycle
4. Select VCF Management, then the Upgrade tab
5. Click Change target version
6. In the Set Target Version dialog, select the version from the dropdown, then
   click Customize
7. For each component, select a version from the Target version dropdown and
   click Set version
8. In the Management component target version section, click Run prechecks for the
   component
9. Remediate any precheck errors
10. Click Upgrade for the component

The **Components tab** in the same view shows every management component with its
FQDN, current version, and status. This is where you verify what you actually have
before and after.

Behavioral note: if an upgrade or patch operation is in progress, you cannot
upgrade or patch another component. Operations serialize.

---

## Upgrading core components (walkthrough)

1. In the Lifecycle pane, expand VCF Instances and select a domain
2. Click the Upgrades tab, then Plan Component Upgrade
3. In the wizard, on Select Components and Target Version, choose the component and
   target version, click Next
4. On Plan Overview, click Submit Plan
5. In the Upgrade Sequence section, on the component card, click Run Prechecks
6. Resolve any issues
7. On the component card, click Schedule or Start Now

Note: you cannot use the patch planner if an existing upgrade plan is present.
Cancel the upgrade plan first to create a patching plan.

---

## Binary and depot management

Binaries come from the Software Depot component. If you are connected to an online
depot, binaries are available directly in the patch planner. If you are not, use
the VCF Download Tool to pull binaries to an offline depot, or download in
disconnected mode.

Practical advice: download binaries before the maintenance window. Watching large
bundles download while a change window burns is a bad use of everyone's time.

Also: back up components before you upgrade or patch them.

---

## The honest part: getting to 9.1 is a project

Steady-state model is better. Migration to it is real work. Prerequisites and
gotchas:

- VCF Management Services requires new IP space. You need a new CIDR block with a
  minimum of 12 free IPs on the management VLAN, plus DNS records. You cannot reuse
  your existing 9.0.2 component IPs, because the old components stay online
  orchestrating the upgrade while the new cluster comes up. Reused IPs would
  collide mid-upgrade.
- VCF Operations is mandatory in VCF 9.x. If you do not have it, it gets installed
  as part of the upgrade.
- Aria Operations must be on 8.18 before it can go to VCF Operations 9.1. If you
  are on something older, that is multiple upgrades before you even start.
- Coming from VCF 5.2.x with Aria Operations 8.x, you upgrade using the VCF
  Operations 9.1 PAK file. After that it is removed from Aria Suite Lifecycle,
  which then only handles Day-N operations for Identity Manager 3.3.x.
- SDDC Manager is still in the flow. The SDDC Manager upgrade itself has not
  changed much for 9.1 and is still initiated from the SDDC Manager client under
  Lifecycle Management > SDDC Manager. The single pane is where you end up, not
  where you start.
- VCF services runtime uses an internal 198.18.0.0/15 range. Make sure that does
  not overlap with your management network. It can be changed to 240.0.0.0/15 or
  250.0.0.0/15 via the JSON deployment spec.
- Broadcom publishes a VCF Upgrade Planning Tool that generates a tailored upgrade
  path. Worth mentioning as a starting point.

---

## Known issue callout (short, 3-4 sentences in the post)

VCF 9.1.0.0 has a documented known issue where fleet lifecycle sub-tasks can
remain displayed as In Progress after a workflow completes successfully. The
release notes describe it as a display issue with components fully operational, and
the documented workaround is None. It can gate subsequent patch operations since
lifecycle operations serialize. A detailed write-up is coming in a follow-up post.
Keep it to a short callout; this post is about the model, not the defect.

---

## Takeaways

- The biggest change is not the UI, it is that one control plane replaced two
  lifecycle systems.
- Learn the fleet versus instance split first. Everything about sequencing follows
  from it.
- Fleet-level management components upgrade before instance-level core components.
  Always.
- Lifecycle operations serialize. One upgrade or patch at a time.
- Download binaries ahead of the maintenance window.
- Getting to 9.1 requires new IP space, DNS, and prerequisite Aria versions. Plan
  it as a project, not a patch.
- The SDDC Manager UI is deprecated. Build the muscle memory in VCF Operations now.

---

## Voice and format rules (strict)

- First person, engineer-to-engineer.
- No em dashes anywhere. Commas, periods, or restructure.
- Short paragraphs, two to four sentences max (WordPress).
- No marketing language. No "seamlessly," "leverage," "empower," "journey," "game
  changer," "revolutionary."
- Do not gush. State the improvement plainly and let it stand.
- Technical terms stay technical. Audience is infrastructure engineers.
- Target 1800 to 2500 words.

---

## Before publishing (screenshot safety)

Check every screenshot for credentials, license keys, or internal hostnames that
should not be public. Flag anything questionable rather than assuming it is fine.
Several recent lab screenshots contain cleartext passwords. Scan carefully.

---

## Image sequencing plan (folders map to post sections)

- images/01-old-way/       -> Section 1 (two lifecycle systems: SDDC Manager, Aria Suite Lifecycle)
- images/02-architecture/  -> Sections 2-3 (VCF Management Services, component lists, fleet vs instance)
- images/03-management-upgrade/ -> Section 4 (Build > Lifecycle > VCF Management > Upgrade)
- images/04-core-upgrade/  -> Section 5 (VCF Instances, Plan Component Upgrade wizard)
- images/05-depot-binaries/ -> Section 6 (Software Depot, Binary Management)

Screenshots not yet dropped in. Draft carries placeholders keyed to these folders.
Once screenshots land, sequence them and write captions.

DROP FOLDER: images/_inbox/  <- dump ALL raw screenshots here in one place.
I will sort them into 01-old-way through 05-depot-binaries, sequence them against
the post sections, and write captions. Original filenames are fine; keep them as-is
so we can talk about specific shots.
