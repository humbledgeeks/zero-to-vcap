# VCF 9.1 Lifecycle: One Control Plane, and the Real Work to Get There

I have spent a lot of the *Zero to VCAP* series standing things up: a FlexPod on VCF, licensing it, wiring it into Active Directory, running Kubernetes on it. What I have not written about yet is the part that eats most of your actual calendar once the lab is built, which is keeping the thing current.

So this post is about lifecycle management in VCF 9.1: how the model works now, and why it is a real step up from what I was doing in the VCF 8.0 U3 and 5.x days.

The steady-state model in 9.1 is genuinely simpler. Getting to 9.1 is not. Both of those are true, and if I only tell you the first one I am setting you up to get burned on the second.

If you want the small-scale companion to this, I already walked through a reduced-downtime [vCenter security patch on VVF 9.1](https://humbledgeeks.com/how-easy-is-it-to-patch-vcenter-in-vvf-91-i-applied-a-critical-security-patch-to-find-out/). That post is a single vCenter with no fleet orchestration at all. This one is the opposite end: the full VCF control plane driving a fleet.

---

## Where we came from: two lifecycle systems

In VCF 8.0 U3 and the 5.x line, you did not operate one lifecycle system. You operated two, side by side, and you were the integration layer between them.

SDDC Manager owned the core infrastructure lifecycle. That meant itself, NSX, vCenter, and the ESXi hosts. You pulled bundles into SDDC Manager, either from an online depot with credentials or by offline bundle transfer for dark sites, and upgrades ran sequentially per workload domain. Management domain first, then the VI workload domains.

VMware Aria Suite Lifecycle owned the other half. This was the management and Aria stack: Aria Operations, Aria Automation, Identity Manager. It started life as vRSLCM, later ASLCM, and it was a separate appliance with its own UI, its own binary management, and its own upgrade workflow.

Here is the part that made it work you had to think about. Aria Suite Lifecycle was decoupled from SDDC Manager after VCF 4.4.1. So sequencing the Aria stack against the core stack was entirely your job. Nothing enforced it for you.

The practical result was two consoles, two binary repositories, two sets of prechecks, and an upgrade order you had to memorize and hold in your head. The order most of us ran was Aria stack first through Aria Suite Lifecycle, then SDDC Manager, then NSX, then vCenter, then ESXi. Get that wrong and you found out the hard way.

![The SDDC Manager dashboard, the single-instance console I ran core lifecycle from, with workload domains and upgrades tracked separately from the Aria stack](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-01-old-way-upgrade_51-scaled.jpg)

![SDDC Manager Binary Management, where I pulled the core bundles for vCenter, NSX, ESX, and SDDC Manager itself before any of it moved into VCF Operations](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-01-old-way-upgrade_1-scaled.jpg)

One more piece of context from this era, because it explains a change you will notice. vSphere Lifecycle Manager baselines still existed then. VCF 9.0 removed baseline support in favor of single image management, and it retired a batch of other long-serving features at the same time: Enhanced Linked Mode, Integrated Windows Authentication, Storage IO Control, Host Profiles, and vVols. If you are coming from an older design that leaned on any of those, that is its own planning conversation.

---

## What VCF 9.1 actually changed

The headline is not a new button. It is that the two lifecycle systems collapsed into one.

Some history so the version numbers make sense. VCF 9.0 introduced a standalone Fleet Management Appliance and a separate VMware Identity Broker appliance cluster. VCF 9.1 removed both of those as standalone appliances and folded their function into a container cluster called VCF Management Services.

Lifecycle in 9.1 is delivered by two services that run natively inside that cluster. The first is Fleet Lifecycle, which owns the fleet-level management components: VCF Operations, Operations for Logs, Operations for Networks, VCF Automation, and the Identity Broker. That is the Aria Suite Lifecycle lineage, absorbed into the platform instead of shipped as its own appliance.

The second is SDDC Lifecycle, which owns the instance-level core components: vCenter, NSX, ESXi hosts, and vSAN. That is the SDDC Manager lineage.

Both services are driven from the VCF Operations console, under Build > Lifecycle. The Software Depot also runs as a component in the same cluster, so binary management is centralized instead of duplicated across two tools.

![The VCF Management components list in VCF Operations. Fleet lifecycle, SDDC lifecycle, Software depot, Identity broker, and Salt each show up as their own service with an FQDN and version, which is the whole architecture in one screen](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-02-architecture-upgrade_45-scaled.jpg)

One thing to know before you build muscle memory around it. The SDDC Manager UI is being deprecated and will be removed in a future release. After you are on 9.1, you perform lifecycle activities from VCF Operations. SDDC Manager still exists in the plumbing, and as you will see it still has a role during the migration, but it is not where you are meant to live day to day anymore.

![The same SDDC Manager UI in 9.1, now carrying a deprecation banner that points lifecycle work to VCF Operations. It still runs, but it is on its way out](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-01-old-way-upgrade_50-scaled.jpg)

---

## The fleet versus instance model

This is the concept that makes everything else make sense, so it gets its own section. If you learn one thing from this post, learn this split.

Components in VCF 9.1 are either fleet-level or instance-level, and that distinction decides where they live and when they upgrade.

Fleet-level components are shared across every VCF instance you run. Fleet Lifecycle, Salt RaaS, the Software Depot, and the license server are deployed once and serve the whole fleet. When you add a second or third VCF instance, only VCF Services Runtime, Salt master, and SDDC Lifecycle get deployed for that new instance. The fleet components are shared from the first instance rather than rebuilt.

Instance-level components are per VCF instance. vCenter, NSX, ESXi, vSAN, and SDDC Lifecycle exist once per instance, because each instance has its own.

Now the payoff, which is the governing rule for sequencing. You upgrade the fleet-level management components first, then the instance-level core components. Fleet gates instance, never the reverse. You start with the VCF instance that hosts the VCF Operations instance managing your fleet, then work outward to the workload domains.

Read that rule again, because it is doing a lot of work. It replaces almost all of the sequencing knowledge you used to carry in your head for the two-tool model. Instead of memorizing Aria-then-SDDC-then-NSX-then-vCenter-then-ESXi across two consoles, you remember fleet before instance, from the managing instance outward. That is the whole thing.

![A component detail view that separates the fleet components FQDN from the instance components FQDN. That split is what decides which services are shared across instances and which are per instance](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-02-architecture-upgrade_26-scaled.jpg)

![Fleet Management in VCF Operations, where the console sees VCF Management, the VCF instances, and any standalone vCenters as one fleet](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-02-architecture-upgrade_30-scaled.jpg)

---

## Upgrading the management components

Let me walk the fleet-level upgrade, since that is what you touch first. This all happens in VCF Operations.

Log in to VCF Operations, go to Build in the top navigation, and pick Lifecycle in the left pane. Select VCF Management, then the Upgrade tab. This is the fleet side of the house.

Click Change target version. In the Set Target Version dialog, pick the version from the dropdown, then click Customize. Customize is where you get per-component control instead of a single blanket target.

For each component, select a version from the Target version dropdown and click Set version. You are telling each management component where it is going.

Then, in the Management component target version section, click Run prechecks for the component. Remediate anything the prechecks flag before you go further. Prechecks are the gate, and a warning here is the upgrade telling you what it is about to trip on. Once it is clean, click Upgrade for that component.

![Change target version opens the Set Target Version dialog, where I pick the fleet target build from the dropdown and set it](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_42-scaled.jpg)

![With the target set, every management component resolves to a current-to-target path and reads Ready for upgrade](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_19-scaled.jpg)

![Selecting all nine components turns the actions into Run Prechecks and Upgrade for the whole set](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_13-scaled.jpg)

![The confirmation dialog is the commit point. It reminds you to pass prechecks first, which the tool means literally](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_14-scaled.jpg)

![The Tasks tab breaks the run into named subtasks: set context, stage plugin, run prechecks, stage package, prepare, upgrade, then inventory sync](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_21-scaled.jpg)

![Back on the Components tab afterward, every management service reads its new target build. This is where I confirm what actually landed](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-03-management-upgrade-upgrade_6-scaled.jpg)

Two things worth knowing while you are in here. The Components tab in the same view lists every management component with its FQDN, current version, and status. That is where you confirm what you actually have, both before you start and after you finish, rather than trusting that the upgrade did what you asked.

The second thing is a behavior you will hit eventually. If an upgrade or patch operation is already in progress, you cannot upgrade or patch another component. Operations serialize. One at a time, on purpose.

---

## Upgrading the core components

Once the fleet-level management components are current, you move to the instance-level core components. Same console, different pane.

In the Lifecycle pane, expand VCF Instances and select a domain. Click the Upgrades tab, then Plan Component Upgrade. The word "plan" matters here, because core upgrades are built as a plan you submit, not a single button.

In the wizard, on Select Components and Target Version, choose the component and its target version, then click Next. On Plan Overview, click Submit Plan. You have now staged the plan.

In the Upgrade Sequence section, find the component card and click Run Prechecks. Resolve anything it raises. When the card is clean, click Schedule or Start Now, depending on whether you are driving this into a change window later or running it now.

![On the dc3-wld01 workload domain, the Upgrades tab runs its own prechecks before any core component moves. This is the instance-level side, and it only starts after the fleet components are current](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-04-core-upgrade-upgrade_32-scaled.jpg)



One gotcha to file away. You cannot use the patch planner if an existing upgrade plan is already present. If you need to build a patching plan, cancel the upgrade plan first. It is a small thing, but it will stop you cold if you do not know it is there.

This is where the fleet-versus-instance rule pays off in practice. You did the management side first, and only now are you touching vCenter, NSX, ESXi, and vSAN, working out from the instance that runs your managing VCF Operations. You are not sequencing two tools against each other. You are following one order.

---

## Binary and depot management

None of this moves without binaries, and in 9.1 they come from the Software Depot component that runs in the same cluster.

If you are connected to an online depot, the binaries are available directly in the patch planner. There is nothing extra to stage. If you are not connected, which covers dark sites and a lot of real production, you use the VCF Download Tool to pull binaries to an offline depot, or you download in disconnected mode.

![The Software Depot connection mode. Connected pulls from Broadcom online, while Offline Depot and Disconnected cover dark sites](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-05-depot-binaries-upgrade_48-scaled.jpg)

![The Register step ties the depot to Broadcom with an activation code. This is the redacted copy of that screen](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-05-depot-binaries-upgrade_47-scaled.jpg)

![The Software Depot overview shows the connected depot and its storage, which is where downloaded bundles live for the patch planner](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-05-depot-binaries-upgrade_49-scaled.jpg)

![The VCF Installer side of the depot, with the vSphere Foundation and Cloud Foundation bundles already downloaded before any deploy or upgrade](https://humbledgeeks.com/wp-content/uploads/2026/07/vcf91-lifecycle-05-depot-binaries-upgrade_56-scaled.jpg)

Two pieces of advice that are boring and will save your evening. Download the binaries before the maintenance window opens. Watching multi-gigabyte bundles crawl in while a change window burns is a bad use of everyone's time, and it is the kind of thing that turns a clean plan into an overrun.

And back up your components before you upgrade or patch them. The tooling is better now, but "better tooling" is not a restore point.

---

## The honest part: getting to 9.1 is a project

Everything above is the steady state, and the steady state is good. The migration to reach it is real work, and this is the section that keeps the post honest.

The one that surprises people first is IP space. VCF Management Services requires new IP space, specifically a new CIDR block with a minimum of 12 free IPs on the management VLAN, plus DNS records to match.

You cannot reuse your existing 9.0.2 component IPs. The old components stay online orchestrating the upgrade while the new cluster comes up, so reused addresses would collide mid-upgrade. Plan the addresses and DNS before you touch anything.

VCF Operations is mandatory in VCF 9.x. If you do not already run it, it gets installed as part of the upgrade, so it is not optional and you should plan for it to be there.

If you do run the Aria stack today, mind the version floor. Aria Operations has to be on 8.18 before it can move to VCF Operations 9.1. If you are on something older, that is one or more upgrades you have to complete before you even start the 9.1 work.

The path from 5.2.x is worth calling out specifically. Coming from VCF 5.2.x with Aria Operations 8.x, you upgrade using the VCF Operations 9.1 PAK file. After that, VCF Operations is removed from Aria Suite Lifecycle, and Aria Suite Lifecycle then only handles Day-N operations for Identity Manager 3.3.x. So the old lifecycle tool does not vanish on day one, it shrinks to a narrow remaining job.

SDDC Manager is still in the flow, which trips people who read "one console" too literally. The SDDC Manager upgrade itself has not changed much for 9.1, and it is still initiated from the SDDC Manager client under Lifecycle Management > SDDC Manager. The single pane in VCF Operations is where you end up, not where you start.

Two more that live in the networking weeds. VCF Services Runtime uses an internal 198.18.0.0/15 range, and you need to make sure that does not overlap with your management network. If it does, you can change it to 240.0.0.0/15 or 250.0.0.0/15 through the JSON deployment spec, but you want to catch that before deployment, not after.

Last, do not freehand the path. Broadcom publishes a VCF Upgrade Planning Tool that generates a tailored upgrade path for your starting point. Start there, then map it against the prerequisites above.

---

## One known issue worth planning for

One thing to have on your radar: VCF 9.1.0.0 has a documented known issue where fleet lifecycle sub-tasks can stay displayed as In Progress after a workflow has actually completed successfully. The release notes describe it as a display issue with the components fully operational, and the documented workaround is None. Because lifecycle operations serialize, that lingering In Progress state can gate subsequent patch operations, so it is worth knowing before it stops you. I am going to write this one up in more detail in a follow-up post.

---

## What I would tell someone planning this

If you are staring at a 9.1 upgrade and wondering where to spend your prep time, here is where I would put it.

Spend it on the prerequisites, not the clicks. The console workflow is short, and the prechecks catch most of what you get wrong inside the tool. The things that sink a window are upstream: IP space you did not reserve, DNS you did not create, an Aria version below the floor, an internal range that overlaps your management network.

Learn the fleet-versus-instance split before you learn the buttons. Once that rule is in your head, the sequence stops being something you look up. Fleet before instance, from the managing instance outward.

And treat the transition and the steady state as two different animals. The transition is a project with a change plan, a window, and a rollback story. The steady state, once you are there, is the simpler thing this whole post is about.

---

## Takeaways

- The biggest change is not the UI, it is that one control plane replaced two lifecycle systems.
- Learn the fleet versus instance split first. Everything about sequencing follows from it.
- Fleet-level management components upgrade before instance-level core components. Always.
- Lifecycle operations serialize. One upgrade or patch at a time.
- Download binaries ahead of the maintenance window.
- Getting to 9.1 requires new IP space, DNS, and prerequisite Aria versions. Plan it as a project, not a patch.
- The SDDC Manager UI is deprecated. Build the muscle memory in VCF Operations now.

If you want the small-scale version of this story first, the [VVF 9.1 vCenter patch walkthrough](https://humbledgeeks.com/how-easy-is-it-to-patch-vcenter-in-vvf-91-i-applied-a-critical-security-patch-to-find-out/) is a single vCenter with no fleet at all. This post is what that easy-button lifecycle looks like once there is a whole fleet behind it, and once you have done the project to get there.


