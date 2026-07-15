---
title: "Running DOOM on Kubernetes: vSphere Kubernetes Service (VKS) on My FlexPod VCF 9.1"
date: 2026-07-05
tags: [VCF, VMware Cloud Foundation, 9.1, Kubernetes, VKS, vSphere Kubernetes Service, Supervisor, NSX VPC, FlexPod, Cisco UCS, NetApp, Kubedoom, Doom]
draft: true
---

<!-- ============================================================
CLEAN WALKTHROUGH — the path that worked, end to end.
The VKS cluster was built with the vSphere Client's CREATE CLUSTER wizard (GUI),
v1.35.5 / ClusterClass builtin-generic-v3.6.0. The CLI/manifest version of Step 8-9
(v1.32.10) is preserved in _step8-9-cli-manifest-alt.md for the companion post.
Troubleshooting (the NSX north-south / inbound-reachability saga) is intentionally
left out and will be its own companion post.
Screenshots: vks-NN-*.jpg (Steps 1-7) and kubedoom_NN.jpg (Steps 8-12), workflow order.
============================================================ -->

I'm old enough to remember installing **DOOM** off a stack of floppy disks, killing the
afternoon fragging demons on a beige tower, and being absolutely certain that nothing in
computing would ever be cooler. Turns out I wasn't alone: in the thirty years since, people
have ported DOOM onto pregnancy tests, smart fridges, ATMs, oscilloscopes, and lawnmower
displays — *"can it run DOOM?"* became computing's only universal benchmark. So there's a
certain inevitability to where this post ends up. If DOOM can run on a thermostat, it can
absolutely run on a FlexPod.

Decades later, I'm a Solutions Architect who racks Cisco UCS and NetApp for a living — and
somewhere along the way I made peace with the fact that "fun" and "enterprise
infrastructure" don't usually show up in the same sentence. This post is my attempt to put
them there anyway.

Then I stumbled onto one of [William Lam's](https://williamlam.com/) posts and saw
[**Kubedoom**](https://github.com/storax/kubedoom): a build of DOOM where the on-screen
demons *are live [Kubernetes](https://kubernetes.io/) pods*, and shooting one runs a real
`kubectl delete`. Game over for the demon, game over for the pod. I laughed out loud — and
immediately knew what my **first real workload on VKS** was going to be. Not nginx. Not a
hello-world. **DOOM.**

So this post is me shamelessly copying Lam's demo and showcasing it on my own gear: taking
this **FlexPod VCF 9.1** environment — the one I've spent the last few posts
[licensing](https://humbledgeeks.com/?p=2125) and [wiring into Active Directory](https://humbledgeeks.com/?p=2199) — and finally making it run a *modern
app*. We'll stand up a real, conformant **3 control-plane + 2 worker** Kubernetes cluster
on the workload domain with [**vSphere Kubernetes Service (VKS)**](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-service-administration-and-development/9-0/managing-vsphere-kubernetes-service/running-tkg-service-clusters/deploying-tkg-service-clusters.html), and then deploy the only
container that matters. Killing demons to kill pods. Let's go. 🎮

This runs on a [**FlexPod**](https://www.cisco.com/site/us/en/solutions/computing/converged-infrastructure/flexpod/index.html) — Cisco UCS compute, NetApp ASA30 storage — with VCF 9.1, a workload
domain (`dc3-vc02` / `dc3-wld01`), and [**NSX with VPC networking**](https://www.vmware.com/products/cloud-infrastructure/nsx) (`dc3-nsx01`). The
vSphere Supervisor was enabled when the workload domain was deployed, so we pick up from an
**enabled-but-empty Supervisor**.

---

## How modern apps land on VCF 9.1 (read this first)

Three layers, don't conflate them:

- **The Supervisor** is the Kubernetes control plane *embedded in vSphere* — it turns your
  ESX cluster into a platform. Enabled once (done at workload-domain deploy).
- **A VKS cluster** (formerly a TKG "guest" cluster) is a full, conformant, upstream-aligned
  Kubernetes cluster that VKS provisions *on top of* the Supervisor — its own control-plane
  and worker node VMs, its own kubeconfig. **You deploy Kubedoom into the VKS cluster, not
  the Supervisor.**
- **A vSphere Namespace** bounds what a VKS cluster can consume: compute (VM classes),
  storage (a VM storage policy), the Kubernetes version (a VKr — vSphere Kubernetes Release
  — from a content library), and who can use it (RBAC).

A VKS cluster is the intersection of those three things. Most of this post is making them
true for one namespace, then walking the **CREATE CLUSTER** wizard.

**Two things that are new/important on 9.1:**

- **NSX VPC networking.** On an NSX-VPC Supervisor, the older `TanzuKubernetesCluster` API
  is **not supported** — clusters are the modern [CAPI](https://cluster-api.sigs.k8s.io/) **`Cluster` + ClusterClass** API
  (`builtin-generic-vX.Y.Z`). The vSphere Client's **CREATE CLUSTER** wizard builds that
  object for you; if you go the CLI route instead, the webhook rejects the old TKC manifest
  bluntly (see the companion CLI walkthrough).
- **The VCF CLI.** kubectl access tooling is now the **VCF CLI** (`vcf`), which logs in with
  `vcf context create`. The old `kubectl-vsphere` plugin still ships but is deprecated.

---

## Prerequisites (validate, don't assume)

1. **Supervisor enabled and healthy** on the workload domain — Config Status **Running**,
   Kubernetes Status **Ready**, Node Health **Healthy**.
2. **NSX VPC networking** confirmed on the Supervisor.
3. **A VKr content library** associated with VKS, releases synced.
4. **A VM Storage Policy** available to the namespace (`supervisor`, NetApp ASA30-backed).
5. **VM classes** to bind to the namespace.
6. **AD-backed identity** with rights on the namespace.
7. **A workstation that can reach the Supervisor API**, with the VCF CLI + `kubectl`.

---

## What you'll need on hand (this environment's values)

| Field | Value |
|---|---|
| Workload domain vCenter | `dc3-vc02` (`dc3-wld01`) |
| Supervisor | `dc3-mgmt-supervisor` (Datacenter `dc3-wld01-DC`, 4 hosts) |
| Supervisor networking | **NSX VPC** (NSX Project `Default`, Default VPC Connectivity Profile) |
| vSphere Namespace | `vks-doom` |
| VM Storage Policy / class | `supervisor` (NetApp ASA30-backed) |
| VM classes | `best-effort-medium` (2 vCPU/8 GB) · `best-effort-large` (4 vCPU/16 GB) |
| VKr content library | **Kubernetes Service Content Library** (subscribed, full catalog) |
| Guest cluster | `vks-doom-cl01`, **3 control-plane + 2 workers** (node pool `…-np-97dl`) |
| Guest Kubernetes version (VKr) | `v1.35.5+vmware.1-vkr.1` (Ready + Compatible) |
| ClusterClass | `builtin-generic-v3.6.0` |
| Node OS image | Photon 5 (`photon-5-amd64-v1.35.5---vmware.1-vkr.1`, pulled on demand) |
| Kubedoom manifest | `kubedoom.yaml` (Kubedoom, `ghcr.io/storax/kubedoom`) |

---

## Step 1 — Log in and validate the Supervisor

Log in to the **vSphere Client** on `dc3-vc02` with an **AD account** (UPN form). My lab's
internal CA isn't browser-trusted, so I get the usual "your connection isn't private" — a
lab reality, not a problem.

![Browser certificate warning for dc3-vc02](vks-images/vks-01-cert-warning.jpg)

*Lab honesty: the internal CA isn't trusted yet, so the browser complains. Continue through — production hygiene is CA-signing this later.*

The login itself is **VCF SSO** — Active Directory doing the work from the last post, no
local `@vsphere.local` account in sight.

![vSphere VCF SSO login page](vks-images/vks-02-vcf-sso-login.jpg)

*Login method = VCF SSO. AD credentials all the way down.*

Before anything, confirm this really is a **9.1 FlexPod**. A host check shows **ESXi
9.1.0.0100** on a **Cisco UCSB-B200-M5** blade in cluster `dc3-wld-cl01` — the version and
the hardware the whole "what changed in 9.1" story depends on.

![Host dc3-hst-esxi08 summary: ESXi 9.1, UCS B200-M5](vks-images/vks-03-esxi91-ucs-host.jpg)

*ESXi 9.1.0.0100 on UCS B200 hardware, workload cluster `dc3-wld-cl01`. This is the FlexPod the cluster will land on.*

Now to the Supervisor. **Workload Management / Supervisor Management → Namespaces** shows
the enabled-but-empty state: only the system namespaces (`svc-cci-ns`, `svc-tkg`,
`svc-velero`), all Running. No user namespace yet — exactly where we start.

![Supervisor Management Namespaces — only system namespaces](vks-images/vks-04-supervisor-namespaces.jpg)

*Enabled but empty. Those `svc-*` namespaces are the Supervisor's own services (the consumption interface, the VKS/TKG service, backup).*

The **Supervisors** tab is the health gate: `dc3-mgmt-supervisor`, **Config Status Running**,
**Host Config Status Running**, 4 hosts, on `dc3-vc02`.

![Supervisors tab — Config Status Running, 4 hosts](vks-images/vks-05-supervisors-tab.jpg)

*Green across the board. The "mgmt" in the name is cosmetic — its Datacenter is `dc3-wld01-DC`, so it's genuinely the workload-domain Supervisor.*

Open the Supervisor's **Summary** and confirm **Kubernetes Status Ready**, **Node Health
Healthy**, and that **Kubernetes Service** already has **1 content library** associated
(that's the VKr library — one prerequisite already satisfied).

![Supervisor Summary — Ready, Healthy, 1 content library](vks-images/vks-06-supervisor-summary.jpg)

*Ready and Healthy, with the Kubernetes Service content library already attached. The control plane lives on the management subnet; the API is exposed via the VPC.*

**Configure → Network → Workload Networks** is the one that matters for clusters: it states
plainly that the network is **supported by NSX VPC**.

![Supervisor Configure → Network, Workload Networks = NSX VPC](vks-images/vks-07-workload-network-nsxvpc.jpg)

*NSX VPC confirmed. This single fact is why the modern CAPI Cluster API is the only option here — the old TanzuKubernetesCluster manifest gets rejected on NSX VPC (more on that at Step 8).*

Scroll up and you'll see the **External IP Blocks** — `vpc-external-10.103.50.0/24`. That's
the pool your clusters' API endpoints and any `LoadBalancer` services draw from.

![Supervisor external IP blocks — vpc-external-10.103.50.0/24](vks-images/vks-08-external-ip-blocks.jpg)

*The VPC external block. Every cluster API and LoadBalancer VIP comes out of here.*

---

## Step 2 — Create the vSphere Namespace

Back on **Namespaces**, click **NEW NAMESPACE**.

![Namespaces tab with NEW NAMESPACE](vks-images/vks-09-namespaces-new.jpg)

*The namespace is the boundary that bounds the cluster's compute, storage, and access.*

**Location** — pick the Supervisor (`dc3-mgmt-supervisor`).

![Create Namespace — Location, select Supervisor](vks-images/vks-10-namespace-location.jpg)

**Configuration** — name it **`vks-doom`** (DNS-compliant: lowercase, no spaces). I added a
description, because future-me appreciates context, and left the network override unchecked
so it inherits the NSX VPC backing.

![Create Namespace — name vks-doom, description, no network override](vks-images/vks-11-namespace-config.jpg)

*Name can't be changed after creation, so get it right. "Demo of DOOM-POD" — no notes.*

**Add Zones** — there's one zone (`dc3-zone1`); take it.

![Create Namespace — Add Zones](vks-images/vks-12-namespace-zones.jpg)

**Review** and finish.

![Create Namespace — Review](vks-images/vks-13-namespace-review.jpg)

*Name, Supervisor, zone — confirmed. Click FINISH.*

A few seconds later: **"Your namespace vks-doom has been successfully created."** Config
Status flips Configuring → Running.

![Namespace vks-doom created successfully](vks-images/vks-14-namespace-created.jpg)

*Created. Note the suggested next actions — storage policies, permissions, content library — which is exactly our plan.*

---

## Step 3 — Assign a VM Storage Policy

On `vks-doom`, the Storage card prompts **ADD STORAGE**.

![Namespace Summary — ADD STORAGE](vks-images/vks-15-add-storage-button.jpg)

There's exactly one policy — **`supervisor`** (10 TB total, backed by the NetApp ASA30).
No decision to agonize over.

![Select Storage Policies — supervisor](vks-images/vks-16-select-storage-policy.jpg)

*This policy maps to the FlexPod's NetApp datastore. It becomes the cluster's Kubernetes storage class.*

Select it and click OK.

![Select Storage Policies — supervisor selected, OK](vks-images/vks-17-storage-policy-ok.jpg)

The Storage card now shows **supervisor | No limit**.

![Namespace Summary — storage policy added](vks-images/vks-18-storage-added.jpg)

*Added with "No limit" — fine for a lab; in production you'd cap the namespace so one team can't eat the datastore.*

---

## Step 4 — Add VM Classes

The VM Service card prompts **ADD VM CLASS** — the size of each node VM.

![Namespace Summary — ADD VM CLASS](vks-images/vks-19-namespace-pre-vmclass.jpg)

You get the full menu of system t-shirt sizes.

![Add VM Class — the available classes](vks-images/vks-20-add-vmclass-list.jpg)

*Whatever you bind here is the only set of sizes the cluster can pick from.*

I selected **`best-effort-medium`** (2 vCPU/8 GB) for control-plane nodes and — out of old
habit — **`best-effort-4xlarge`** for workers.

![Add VM Class — selecting classes](vks-images/vks-21-add-vmclass-select.jpg)

Then I caught myself: `4xlarge` is **16 vCPU / 128 GB per node** — 256 GB of RAM for two
workers to run a Doom container. I went back into **Manage VM Classes** and swapped it for
**`best-effort-large`** (4 vCPU/16 GB).

![Manage VM Classes — swap 4xlarge for large](vks-images/vks-22-manage-vmclass-swap.jpg)

*Right-size deliberately. Don't grab giant node classes just because the capacity exists.*

The VM Service card settles on **2 Associated VM Classes**.

![Namespace Summary — 2 VM classes associated](vks-images/vks-23-vmclass-result.jpg)

![VM Service card — Manage VM Classes](vks-images/vks-24-vmservice-card.jpg)

*`medium` for the control plane, `large` for workers — sensible and still roomy.*

---

## Step 5 — Permissions (and an honest least-privilege note)

I'm logged in as `admin.allen` — a real **AD** account (SSO doing its job) that also carries
VCF/vSphere admin rights, so it already inherits full access to the namespace. For a lab of
one, there's nothing to add. But the *point* of a vSphere Namespace — and of the AD/SSO work
from the last post — is **least privilege**: in production you'd add a scoped AD group as
**Can edit** and never let the platform consume a Domain Admin credential. The Permissions
tab is exactly where that handoff happens.

*No screenshot — the point is the caveat.*

---

## Step 6 — Confirm the VKr content library

**Menu → Content Libraries → Kubernetes Service Content Library.** It should be
**Subscribed**, **auto-synced**, with the VKr (Kubernetes release) catalog present.

![Content Libraries — Kubernetes Service Content Library](vks-images/vks-25-content-library.jpg)

![Content Library detail — subscribed, synced, templates](vks-images/vks-26-content-library-detail.jpg)

*Subscribed with the full release catalog. A subscribed VKr library syncs metadata and pulls the node-image OVA on demand when a cluster needs it. No VKr, no selectable Kubernetes version.*

---

## Step 7 — Install the VCF CLI + kubectl and log in

From the **`vks-doom` Summary → Link to CLI Tools**, you land on the **VCF Consumption CLI**
download page (served by the Supervisor API endpoint).

![Kubernetes CLI Tools / VCF Consumption CLI page](vks-images/vks-27-cli-tools-page.jpg)

*The new `vcf` CLI is the headline tool; the deprecated `kubectl-vsphere` plugin (which bundles `kubectl.exe`) is still here in an expandable section — grab both.*

Downloaded and extracted.

![Downloads — vcf-cli and vsphere-plugin](vks-images/vks-28-cli-download.jpg)

Log in to the Supervisor with the VCF CLI. The internal cert means `--insecure-skip-tls-verify`,
and auth is your AD account:

```powershell
vcf context create --endpoint=<supervisor-api-fqdn> --insecure-skip-tls-verify
#   name it (dc3-supervisor); auth = admin.allen@humbledgeeks.com
```

![vcf context create — logged in successfully, all contexts saved](vks-images/vks-29-vcf-login-success.jpg)

*"Logged in successfully" — and every namespace context is saved, including `dc3-supervisor:vks-doom`. AD credentials at the CLI too.*

Switch into the namespace context:

```powershell
vcf context use dc3-supervisor:vks-doom
```

![vcf context use vks-doom — Harbor warning](vks-images/vks-30-context-harbor-warning.jpg)

*Heads-up: a "failed to discover plugin sources from the system Harbor registry" warning is normal if Regional Harbor isn't configured — it only affects optional VCF CLI plugins; `kubectl` works fine. (Harbor is a VKS add-on-image dependency, so if a cluster never reaches Ready, look there.)*

Confirm `kubectl` (from the plugin bundle) is wired up:

```powershell
kubectl version --client
kubectl config use-context dc3-supervisor:vks-doom
```

![kubectl version --client](vks-images/vks-31-kubectl-version.jpg)

And the green light — `kubectl get ns` returns the namespaces, including `vks-doom`:

```powershell
kubectl get ns
```

![kubectl get ns — vks-doom Active](vks-images/vks-32-kubectl-get-ns.jpg)

*Full working API access. We're operational.*

---

## Step 8 — Create the VKS cluster (3 control-plane + 2 workers)

On an NSX-VPC Supervisor you can drive the whole cluster build from the vSphere Client — it
assembles the CAPI `Cluster` object behind the scenes. (Prefer YAML? The full
`kubectl`/manifest version of this step lives in the companion CLI walkthrough.)

From the `vks-doom` namespace, open the **Resources** tab and click **CREATE CLUSTER**. The
namespace is still empty — 0 clusters — but 74 VM Images are already synced from the content
library, and there's 1 Network Service from NSX VPC.

![vks-doom namespace Resources tab — CREATE CLUSTER](vks-images/vks-43-create-cluster-resources.jpg)

*The launch point. The 74 VM Images are the VKr catalog the wizard will offer; the Network Service is the NSX VPC backing.*

**Step 1 — Configuration Type.** Cluster Type **Cluster API**, and I picked **Custom
Configuration** so I could set replica counts and node sizes explicitly (Default
Configuration is a fixed starter).

![Wizard Step 1 — Cluster API, Custom Configuration](vks-images/vks-44-config-type-custom.jpg)

*Custom Configuration = you choose CP/worker counts, VM classes, and storage. The right pane shows the live Kubernetes Resource YAML the wizard is building — the same `Cluster` object you'd otherwise hand-write.*

**Step 2 — General Settings.** Name the cluster **`vks-doom-cl01`**, pick **Cluster Class
`builtin-generic-v3.6.0`** and **Kubernetes Release `v1.35.5+vmware.1-vkr.1`** (Ready +
Compatible), and select VM Class **`best-effort-medium`** (2 vCPU / 8 GB) and Storage Class
**`supervisor`**.

![Wizard Step 2 — General Settings, vks-doom-cl01, v1.35.5, best-effort-medium](vks-images/vks-45-general-settings.jpg)

*The wizard defaults the name to something like `kubernetes-cluster-mfzs` — rename it. `best-effort-medium` is plenty for a Kubedoom demo; the larger classes are there if you ever run something real.*

**Step 3 — Control plane.** Set **Replicas = 3** for an HA control plane and confirm the OS
Image is **Photon 5** from the Kubernetes Service Content Library.

![Wizard Step 3 — Control plane, 3 replicas, Photon 5](vks-images/vks-46-controlplane-3replicas.jpg)

*Three control-plane nodes = etcd quorum survives one node failing. One replica is fine for throwaway labs; I wanted this to look like something a sponsor would take seriously.*

**Step 4 — Node pools.** Add a worker pool (the wizard names it **`vks-doom-cl01-np-97dl`**),
zone `dc3-zone1` (Automatic), **Replicas = 2**, same `best-effort-medium` / `supervisor`.

![Wizard Step 4 — node pool, 2 replicas](vks-images/vks-47-nodepool-2replicas.jpg)

*Two workers to actually run pods. The node-pool name is auto-generated — note it; it shows up later in `kubectl get nodes`.*

**Step 5 — Review and Confirm.** The summary reads back 3 control-plane + 1 node pool (2
workers), v1.35.5, `builtin-generic-v3.6.0`, `best-effort-medium`, `supervisor`. The right
pane is the final `Cluster` YAML. **FINISH.**

![Wizard Step 5 — Review and Confirm, FINISH](vks-images/vks-48-review-finish.jpg)

*Everything the wizard did is right there as declarative YAML — copy it out and you've got your manifest for next time.*

---

## Step 9 — Watch it provision

The vSphere Client shows the cluster come to life. First a green banner —
**"Cluster 'vks-doom-cl01' is being created"** — and the cluster row sits at Status
**Unknown**.

![Cluster being created — Status Unknown](vks-images/vks-49-cluster-being-created.jpg)

Under the covers, the first thing that happens is a **Sync Library Item** task pulling the
**Photon 5 node OVA** (`photon-5-amd64-v1.35.5---vmware.1-vkr.1`) on demand — a subscribed
VKr library only fetches the image when a cluster actually needs it.

![Recent Task — Sync Library Item, Photon 5 OVA](vks-images/vks-50-sync-library-item.jpg)

*This on-demand pull is why the very first cluster of a given version takes a few extra minutes — the OVA has to land before any node VM can clone from it.*

Then the node VMs clone, boot, and join (you'll see "Promote virtual machine disks" tasks on
the `np-97dl` workers), and the cluster flips to **Status: Available** — **about four
minutes** start to finish on this FlexPod.

![Cluster Available — 4 minutes](vks-images/vks-51-cluster-available.jpg)

*Available = the control plane is up and reachable. The whole HA cluster — 3 control-plane + 2 workers — stood up in roughly four minutes on Cisco UCS + NetApp.*

(Prefer to watch from the CLI? `kubectl get cluster,machine -n vks-doom -w` shows the same
thing — 5 Machines going Pending → Provisioning → Running, the 2nd/3rd control-plane
machines appearing only after the first, as etcd quorum builds in order.)

---

## Step 10 — Log in to the guest cluster

Log straight into the new cluster with `kubectl vsphere login` — point `--server` at the
Supervisor's control-plane address and name the namespace and cluster. (The Supervisor
address here is `10.103.50.5`; yours comes from the VPC external block.)

```powershell
kubectl vsphere login --server=<supervisor-address> `
  --vsphere-username admin.allen@humbledgeeks.com `
  --tanzu-kubernetes-cluster-namespace vks-doom `
  --tanzu-kubernetes-cluster-name vks-doom-cl01 `
  --insecure-skip-tls-verify

kubectl config use-context vks-doom-cl01
kubectl get nodes -o wide
```

![Guest cluster login + kubectl get nodes — 5 nodes Ready](vks-images/vks-52-guest-get-nodes.jpg)

*Five nodes — 3 control-plane + 2 workers (`…-np-97dl-…`) — all Ready, running **v1.35.5+vmware.1** on **Photon OS**, containerd runtime. Internal IPs come from the cluster's network space. This is a real, conformant, HA Kubernetes cluster on the FlexPod.*

---

## Step 11 — Deploy Kubedoom

Kubedoom turns the cluster's pods into the demons in a game of DOOM — shoot a demon and the
pod is really deleted. Here's the manifest I applied: a **privileged** `kubedoom` namespace
(VKS enforces Pod Security Admission, so the pod needs the privileged label or it's
rejected), a **cluster-admin** service account (so Kubedoom can list and delete pods), the
deployment (`ghcr.io/storax/kubedoom:latest`, VNC on **5900**), and a **`LoadBalancer`**
service — which is what makes NSX VPC hand out an external IP.

> **Two things to know:** `ghcr.io/storax/kubedoom` is a public image, so the workers need
> egress to pull it (or mirror it into Regional Harbor). And by default Kubedoom watches the
> **`default`** namespace — so stage your throwaway "demon" pods there.

```yaml
# kubedoom.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kubedoom
  labels:
    pod-security.kubernetes.io/enforce: privileged
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kubedoom
  namespace: kubedoom
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kubedoom
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
  - kind: ServiceAccount
    name: kubedoom
    namespace: kubedoom
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kubedoom
  namespace: kubedoom
  labels:
    app: kubedoom
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kubedoom
  template:
    metadata:
      labels:
        app: kubedoom
    spec:
      serviceAccountName: kubedoom
      containers:
        - name: kubedoom
          image: ghcr.io/storax/kubedoom:latest
          ports:
            - containerPort: 5900
              name: vnc
---
apiVersion: v1
kind: Service
metadata:
  name: kubedoom
  namespace: kubedoom
spec:
  type: LoadBalancer
  selector:
    app: kubedoom
  ports:
    - name: vnc
      port: 5900
      targetPort: 5900
```

Apply it (you're in the `vks-doom-cl01` context from Step 10, so no `--kubeconfig` needed):

```powershell
kubectl apply -f kubedoom.yaml
```

![kubectl apply -f kubedoom.yaml — all objects created](vks-images/vks-53-kubedoom-apply.jpg)

*`namespace / serviceaccount / clusterrolebinding / deployment / service` all created.*

Confirm the pod is Running, stage 8 demons in `default`, then read the service:

```powershell
kubectl get pods -n kubedoom
kubectl create deployment demons --image=nginx --replicas=8
kubectl get svc -n kubedoom
```

![kubedoom pod Running + demons created + LoadBalancer EXTERNAL-IP](vks-images/vks-54-kubedoom-svc-externalip.jpg)

*The payoff line: `kubedoom   LoadBalancer   …   EXTERNAL-IP <10.103.50.x>   5900:…/TCP`. NSX VPC allocated that external IP from the `10.103.50.0/24` block and wired the north-south path to it — the same path that carries the cluster's API. A `LoadBalancer` service getting a real IP is the proof the whole VCF/NSX networking stack works end to end.*

> **No LoadBalancer? No problem.** Skip the external VIP entirely with
> `kubectl -n kubedoom port-forward deploy/kubedoom 5900:5900`, then point a VNC client at
> `localhost:5900`.

---

## Step 12 — Connect to DOOM and kill some pods (rip and tear)

If you were there in the '90s, you remember the gloriously unhinged **1996 DOOM comic** —
the one where the Marine just *loses it* and screams the line that became the franchise's
eternal battle cry: **"Rip and tear, until it is done."** It was such a perfect meme that
id Software eventually made it canon, carving it into DOOM (2016) as the Slayer's mantra.

Fitting, because in Kubedoom you don't rip and tear demons — you rip and tear **pods**.
Every monster on screen is a live Kubernetes pod, and every shot is a real `kubectl delete`.

The demons are already staged (Step 11). Point a VNC client at the LoadBalancer's external
IP on port **5900** — I used TightVNC Viewer from the jumphost:

![TightVNC — connect to the external IP on 5900](vks-images/vks-55-tightvnc-connect.jpg)

The password is **`idbehold`** — and yes, that's a real classic DOOM cheat code (family with
`IDDQD` god-mode and `IDKFA` full-arsenal), reused here as the Kubedoom VNC password. A nice
wink for anyone who misspent their youth the way I did.

![VNC Authentication — password idbehold](vks-images/vks-56-vnc-auth.jpg)

And there it is — **DOOM, rendered from a pod on my FlexPod**: demons on screen, chaingun up,
100% health. Each monster is one of those 8 `demons` pods; line one up, **Ctrl** to fire, and
Kubernetes deletes the pod out from under it (the deployment immediately spins up a
replacement, so the horde keeps coming). Arrow keys move; the classic controls all work.

![Kubedoom — the DOOM screen, the demons are pods](vks-images/vks-57-doom-screen.jpg)

*Thirty years after a stack of floppies and a beige tower, I'm fragging Kubernetes pods on a Cisco UCS + NetApp FlexPod running VCF 9.1. Rip and tear. Worth it.*

---

## Verify

- `kubectl get nodes -o wide` (in the `vks-doom-cl01` context) → 5 nodes Ready, v1.35.5.
- `kubedoom` service shows a `LoadBalancer` EXTERNAL-IP on 5900 (or use port-forward).
- Shooting a demon deletes the mapped pod (watch `kubectl get pods` in `default`).
- The cluster is declarative — the wizard's Review YAML rebuilds it any time.

---

## Gotchas worth keeping

- **Don't deploy DOOM into the Supervisor** — log in to the *VKS cluster's* context
  (`kubectl vsphere login … --tanzu-kubernetes-cluster-name …`), not the Supervisor.
- **`TanzuKubernetesCluster` is rejected on NSX VPC** — the wizard builds the CAPI `Cluster`
  for you; if you go CLI, use the `Cluster` API (see the companion walkthrough).
- **`builtin-generic` variables live in `.status.variables`**, not `.spec.variables` — only
  matters if you hand-write the YAML.
- **Pick a VKr that's Ready *and* Compatible** in the wizard's dropdown.
- **PSA + cluster-admin** — Kubedoom needs the privileged namespace label and is
  cluster-admin; fine for a lab demo, never anywhere real. Tear it down after.
- **First cluster of a version is slower** — the Photon OVA syncs on demand before nodes clone.
- **Regional Harbor** is a VKS add-on-image dependency — if clusters never reach Ready, check it.

---

## What's next

- **Cross-vCenter migration** — bring a VM from the legacy vSphere 8.0U3 environment into
  this workload domain via Advanced Cross vCenter vMotion.
- **Backup and recovery** — VCF-native backup/restore plus the NetApp SnapCenter plug-in.
- **Lifecycle management** — register the software depot and apply an update via VCF Operations.
- **A companion troubleshooting post** — getting here was *not* a clean click-through.
  Before this cluster would form, I spent a long night chasing why nothing on the
  `10.103.50.0/24` external block was reachable. It turned out to be nothing in NSX at all —
  a stray Windows VM squatting on an edge TEP IP, plus a couple of DHCP collisions on the
  overlay VLAN, quietly breaking the GENEVE tunnels. That rabbit hole deserves its own
  write-up. Circling back.

*Next post in the series: the companion troubleshooting deep-dive — how getting this very
cluster to form turned into a long night chasing why nothing on the `10.103.50.0/24`
external block was reachable. Spoiler: it was nothing in NSX at all — a stray Windows VM
squatting on an edge TEP IP, plus a couple of DHCP collisions on the overlay VLAN, quietly
breaking the GENEVE tunnels. Rip and tear, indeed.*

<!-- DRAFT NOTES — remove before publishing
Status: CLEAN success-path draft, COMPLETE through Step 12 (the DOOM screen).
Cluster built via the vSphere Client CREATE CLUSTER wizard (GUI), v1.35.5 / builtin-generic-v3.6.0,
3 control-plane + 2 workers, all best-effort-medium.
Screenshots: Steps 1-7 = vks-01..vks-32; Steps 8-12 = vks-43..vks-57 (clean copies of the kubedoom_NN exports,
spaces/parens stripped so Markdown + the WP build script don't choke).
The CLI/manifest version of Step 8-9 (v1.32.10) is preserved in _step8-9-cli-manifest-alt.md (refs vks-33..vks-42)
for the planned companion troubleshooting post.
Redact before publishing: host FQDNs, the Supervisor control-plane address 10.103.50.5, the LoadBalancer
EXTERNAL-IP 10.103.50.9 and any 10.103.50.x VIPs, and the admin UPN admin.allen@humbledgeeks.com if you prefer.
Kubedoom password 'idbehold' is a public DOOM cheat — fine to show.
Intro links now point to ?p=2125 (licensing) and ?p=2199 (AD SSO) — swap to final permalinks once those publish.
Next-post link at the very end ([link to your next topic]) still a placeholder.
-->
