# CLAUDE.md — Zero to VCAP Project Assistant

You are a dedicated study partner, technical mentor, and blog writing assistant for Allen, who is pursuing the VCAP-VCF Administrator certification (Broadcom Knighthood) and documenting the journey publicly through a blog series called "Zero to VCAP" on HumbledGeeks.com.

---

## 🔄 Current Status — Last Updated 2026-07-15

> **Read this first.** This section is the live handoff context so you can pick up exactly where we left off without re-explaining the history.

### Milestone: Passed VCAP-VCF Storage (3V0-23.25) — June 2026

Allen **passed the VCAP-VCF Storage exam (3V0-23.25, "Advanced VMware Cloud Foundation 9.0 Storage")**. Note this is the **Storage** track, distinct from the VCAP-VCF Administrator goal stated elsewhere in this file. The Knight journey continues; the FlexPod VCF 9.1 lab is still being built out.

### Published Blog Posts (HumbledGeeks.com)

| # | File | Title | Post ID | Status | URL |
|---|------|-------|---------|--------|-----|
| 1 | `zero-to-vcap-vsp-sales-training-detour.md` | VSP Sales Training Detour | — | Live | humbledgeeks.com |
| 2 | `zero-to-vcap-vcffi9-fundamentals.md` | Back to the Foundation: VMware Cloud Foundation Fundamentals | — | Live | humbledgeeks.com |
| 3 | `zero-to-vcap-vmug-connect-minneapolis.md` | VMUG Connect Minneapolis | — | Live | humbledgeeks.com |
| 4 | `zero-to-vcap-study-group-training-access.md` | Study Group & Training Access | — | Live | humbledgeeks.com |
| 5 | `flexpod-vcf-ucs-foundation.md` | Automating a Cisco UCS FlexPod with NetApp ASA A30 on Broadcom VCF | **1794** | **LIVE** | https://humbledgeeks.com/automating-a-cisco-ucs-flexpod-with-netapp-asa-a30-on-broadcom-vcf/ |
| 6 | `blog-posts/zero-to-vcap-vcap-storage-pass.md` | I Passed the Broadcom VCF VCAP Storage Exam | **2079** | **LIVE** | https://humbledgeeks.com/zero-to-vcap-i-passed-the-broadcom-vcf-vcap-storage-exam/ |
| 7 | `vcf-license/zero-to-vcap-flexpod-vcf91-licensing.md` | Licensing My FlexPod (Cisco UCS + NetApp) Broadcom VCF 9.1 Deployment | **2125** | **LIVE** | https://humbledgeeks.com/licensing-my-flexpod-cisco-ucs-netapp-broadcom-vcf-91-deployment/ |
| 8 | `vcf-license/vcf-active-directory-sso.md` | Connecting My FlexPod VCF 9.1 Deployment to Active Directory (VCF Single Sign-On) | **2199** | **LIVE** | https://humbledgeeks.com/connecting-my-flexpod-vcf-91-deployment-to-active-directory-vcf-single-sign-on/ |
| 9 | `vcf-vks/vcf-vks-kubernetes-doom.md` | Running DOOM on Kubernetes: vSphere Kubernetes Service (VKS) on My FlexPod VCF 9.1 | **2256** | **LIVE** | https://humbledgeeks.com/running-doom-on-kubernetes-vsphere-kubernetes-service-vks-on-my-flexpod-vcf-91/ |
| 10 | `vvf-vcenter-upgrade/zero-to-vcap-vvf91-vcenter-upgrade.md` | How Easy Is It to Patch vCenter in VVF 9.1? I Applied a Critical Security Patch to Find Out | **2567** | **LIVE** | https://humbledgeeks.com/how-easy-is-it-to-patch-vcenter-in-vvf-91-i-applied-a-critical-security-patch-to-find-out/ |
| 11 | `VCF-9.1-Lifecycle-Upgrades/draft/zero-to-vcap-vcf91-lifecycle-upgrades.md` | VCF 9.1 Lifecycle: One Control Plane, and the Real Work to Get There | **2595** | **LIVE** | https://humbledgeeks.com/vcf-91-lifecycle-one-control-plane-and-the-real-work-to-get-there/ |

### Most Recent Work (Session 2026-07-15) — VVF 9.1 vCenter security-patch post PUSHED to WP (#2567, DRAFT)

Post #10 is a WordPress **draft (ID 2567)**, `draft: true` (not live). This is a **VVF** (not VCF/dc3) post — the captures are the **e360demo.com** lab (`dc1-vcf-vc01`, `ucs-nodeNN`). Done this session:
- **Opening rewritten** per Allen's ask — friendlier/more exciting, now leads with "just stood up VVF w/ vSAN + migrated everything," the *Zero to VCAP* "looking for things to show in both VVF and VCF" framing, the critical-patch that "popped up," and the **VCF 9.1** teaser ("can't wait to show how easy this is on my much larger VCF 9.1 deployment").
- **NAMING DECISION = KEEP AS-IS** (Allen chose): e360demo.com / `dc1-vcf-vc01` / `ucs-nodeNN` / IPs left visible, **no redaction**. Verified none of the 14 referenced shots expose a plaintext password (the VM-Appliance root-pw screen and VCF Installer "Review Passwords" screen are NOT referenced).
- **Ground-truth corrections against the actual captures:** starting build was **9.1.0.0100 (25417926)**, not "9.1.0.0000/2547926" as drafted — fixed throughout. **Image mapping fixed** (the `upgrade_N` files aren't chronological): pre-flight→`upgrade_2`, Step6 options→`upgrade_9`, Configure-Switchover→`upgrade_7`, Step7 switchover-in-progress→`upgrade_4`, Step8 Switchover-Completed→`upgrade_3`, after-summary→`upgrade_1`. Step5 Network Settings caption/prose changed to **Automatic** (the capture used DHCP, not a typed static temp IP). **`DNS.jpg` dropped** — it's actually a duplicate before-summary, not a DNS check (kept the DNS advice as prose).
- **Pushed** via the image-heavy pattern: `vvf-vcenter-upgrade/build_wp_draft.py` (new; own cache `.wp-media-vvf-map.json`) → `publish.py --no-images --tags "VVF,vCenter,9.1,Reduced Downtime Upgrade,Lifecycle,Zero to VCAP"` → `vcf-license/postprocess_wp.py 2567 --cache vvf-vcenter-upgrade/.wp-media-vvf-map.json --src /dev/null`. **14/14 images canonical**, 0 code blocks, draft-notes intentionally absent. (NOTE: the post-process script lives at `vcf-license/postprocess_wp.py`; there is no `vvf-license/`.)
- **⚠️ STILL TODO before PUBLISHING #2567:** (1) human eyeball the 14 screenshots since names/IPs are intentionally visible; (2) fill the final `[link to your next topic]` placeholder once the upcoming **VCF 9.1 upgrade** post exists (left as-is for now — no target yet); (3) the wizard's VM-Appliance-details root-password shot is out of scope and was not used.

### Prior Work (Session 2026-06-29, later) — VKS/DOOM post PUSHED to WP (#2256)

Post #9 is now a WordPress **draft (ID 2256)**. Done this session:
- **Intro embellished** ("can it run DOOM?" universal-benchmark riff) + **5 SEO links added** (Kubernetes, Kubedoom repo, VKS TechDocs, Cluster API, NSX) on top of the existing William Lam / FlexPod / 2125 / 2199 links. The `[link to your next topic]` placeholder is **filled** with the companion-troubleshooting teaser.
- **Screenshots redacted via OCR** — `vcf-vks/redact_images.py` (tesseract 5.5.2 + pytesseract, installed this session) blacks out `10.103.50.x`, `*.humbledgeeks.com` FQDNs/URLs, and the `admin.allen@humbledgeeks.com` UPN. 36 of 47 images had hits; **all 36 verified clean** by re-OCR, and the **public WP media copies** were OCR-re-checked CLEAN. Originals backed up to `vcf-vks/vks-images/_orig_backup/`. Out-of-scope IPs (172.30.x, 10.109.x, 10.244/10.96/10.250, 10.103.20.11) intentionally left visible.
- **Pushed** via the image-heavy pattern: `vcf-vks/build_vks_doom_draft.py` → `publish.py --no-images --tags …` → `vcf-license/postprocess_wp.py 2256 --cache vcf-vks/.wp-media-vks-map.json --src /dev/null` (the `/dev/null` src skips draft-notes injection — this post keeps none). 47/47 images canonical, 8 code blocks clean.
- **⚠️ STILL TODO before PUBLISHING #2256:** the post **body text** still exposes a few values the screenshots now hide — UPN `admin.allen@humbledgeeks.com` (~Step 7 comment + Step 10 `--vsphere-username`) and `10.103.50.5` (Step 10 prose). The author already placeholdered the endpoint (`<supervisor-api-fqdn>`), so scrub these to match before going live. Also do a human eyeball of the 36 redacted images.

### Earlier Work (Session 2026-06-29, daytime) — VKS / DOOM + S23 Supervisor re-enable

> ✅ **END-OF-DAY UPDATE (2026-06-29, evening) — ALL OF THE MORNING TRIAGE BELOW PASSED. This thread is DONE.** Kept the original morning-triage notes below for history.
>
> - **Supervisor re-enabled cleanly.** **Control Plane Node Address `10.103.50.5`**, Config Status Running, `Test-NetConnection 10.103.50.5 -Port 6443` → True; the external VIP formed this time. **Root cause of the original S23 failure was NOT NSX config** — it was a stray Windows VM (`WIN-D84MIP7VCU4`, MAC `00:50:56:ab:67:66`) squatting on edge TEP `10.103.32.10`, plus duplicate host TEP IPs / DHCP collisions on VLAN 32, breaking the GENEVE overlay. Fixed by removing the Windows VM from VLAN 32, DHCP-excluding the edge block, rebooting edges (reclaimed static .10/.12) and workload hosts (re-leased clean .152+). Proof: `vmkping ++netstack=vxlan -I vmk11 -d -s 8972 10.103.32.10` → 0% loss, ttl=64.
> - **Guest cluster built via the vSphere Client CREATE CLUSTER wizard (GUI, not CLI):** `vks-doom-cl01` in namespace `vks-doom`, ClusterClass **builtin-generic-v3.6.0**, K8s **v1.35.5+vmware.1-vkr.1**, **3 control-plane + 2 workers, all best-effort-medium**, storage `supervisor`, Photon 5. Went **Available in ~4 min**; `kubectl get nodes` = 5 Ready. (The earlier CLI v1.32.10 cluster, stuck on the broken overlay, was deleted.) Guest login = `kubectl vsphere login --server=10.103.50.5 --tanzu-kubernetes-cluster-namespace vks-doom --tanzu-kubernetes-cluster-name vks-doom-cl01`, context `vks-doom-cl01`.
> - **Kubedoom RUNNING — sponsor demo goal (a pod on VKS) MET.** `vcf-vks/kubedoom.yaml` applied to the guest cluster; `kubedoom` LoadBalancer got NSX external IP **10.103.50.9:5900**; 8 `demons` nginx pods staged in `default`; connected via TightVNC (password `idbehold`) → DOOM on screen.
> - **Blog rewritten to match reality.** `vcf-vks/vcf-vks-kubernetes-doom.md`: Steps 8–9 are now the GUI wizard (was CLI), Step 10 `kubectl vsphere login`, Step 11 the actual applied manifest, Step 12 TightVNC + the DOOM screen. New screenshots wired in as **`vks-43..57`** (clean copies of the `kubedoom_NN` exports — spaces/parens stripped so Markdown + the WP build don't choke). The old CLI v1.32.10 Step 8–9 is preserved in **`vcf-vks/_step8-9-cli-manifest-alt.md`** for the planned companion troubleshooting post. Intro links now point to `?p=2125` / `?p=2199`.
> - **Word preview generated:** **`vcf-vks/vcf-vks-kubernetes-doom-PREVIEW.docx`** (pandoc; front matter + draft-notes stripped; 29 pages, 47 images). Rendering preview only — NOT the publish artifact.
> - **⚠️ STILL TODO before publish:** (1) **redact screenshots** — host FQDNs, Supervisor addr `10.103.50.5`, external IP `10.103.50.9`, optionally admin UPN `admin.allen@humbledgeeks.com`; (2) fill the final `[link to your next topic]` placeholder; (3) make sure posts **2125** + **2199** publish before this one (intro links to them); (4) **push to WordPress** — this post has **no post ID yet** (draft on disk only); follow the image-heavy publish pattern (build script → `publish.py --no-images` → `postprocess_wp.py`).

- **VKS / DOOM blog draft (`vcf-vks/vcf-vks-kubernetes-doom.md`, `draft: true`).** Added the famous DOOM tie-ins: Step 12 now opens with **"Rip and tear, until it is done"** (1996 DOOM comic → DOOM 2016 Slayer mantra) framing the pod-killing. Also confirmed the Kubedoom VNC password **`idbehold` is the real DOOM cheat code IDBEHOLD** (family with IDDQD god-mode / IDKFA full-arsenal) — a good easter egg to surface in the post. Steps 10–12 screenshots still **PENDING** until the guest cluster is healthy.

- **S23 remediation — Supervisor RE-ENABLED on a clean base (IN PROGRESS, deploying overnight, FINISH hit ~00:04 2026-06-29).**
  - **Failed `dc3-nsx-edge01` redeploy resolved:** it left an **orphan edge VM with no IP** (the half-built replacement). Allen powered it off (edge cluster stayed `2 Up / Success`), then **deleted it from disk** — clean 2-edge base confirmed (edge01 `.138`/TEP `.32.10`, edge02 `.139`/TEP `.32.12`, 4 tunnels each).
  - **NSX north-south infra verified structurally complete BEFORE re-enabling** (the real S23 pre-check): Default Transit Gateway = Success, External Connection bound to `dc3-mgmt-t0-gw01`, **External IP Block `vpc-external-10.103.50.0-24` present in the Default VPC Connectivity Profile**, N-S Services On, Advertise Rules 1, NAT 2. → Original S23 failure was **NOT** a missing block/profile; it was either convergence/ordering (Supervisor enabled before edges healthy) or a WCP-side LB-VIP creation bug. The clean re-enable is the definitive test.
  - **"Activate a Supervisor" wizard settings (workload vCenter `dc3-vc02`, VCF Networking with VPC):** Cluster deployment on `dc3-wld-cl01` (auto-zone `dc3-zone1`), name **`dc3-wld01-supervisor`**, CP-HA Disabled, storage `supervisor` ×3. Mgmt = **Static** on `wld-cls-vds-01-pg-mgmt`, IPs `10.103.16.65–69`, mask `255.255.255.0`, gw `10.103.16.1`, DNS/NTP `10.103.20.11/.12`, domain `humbledgeeks.com`. Workload = Default VPC Connectivity Profile, External `10.103.50.0/24`, TGW-private `10.250.0.0/16`, **Private (VPC) CIDR `172.30.0.0/16` + Service CIDR `172.29.0.0/16` (kept wizard defaults ON PURPOSE — `10.96.x` would COLLIDE with the guest cluster's `10.96.0.0/16` service CIDR in the CAPI manifest)**. CP size Small. **API Server DNS Name left BLANK** (pre-setting it to the dead VIP caused churn last time — add the A record AFTER the external IP forms).
  - **Plan B held in reserve:** the `dc3-zone1-supervisor-mgmt` network. Only try it if the flat-mgmt re-enable still fails to form the external VIP (change one variable at a time).

- **⏰ MORNING TRIAGE (pick up here):**
  1. Workload Management → `dc3-wld01-supervisor` → **Config Status** (Running = good; still "Configuring" after ~8h = stuck → debug).
  2. **VERDICT SIGNAL (the object that never formed last time):** Supervisor **Control Plane Node Address** = a `10.103.50.x` IP **AND** NSX → VPCs → **External IPs** shows an allocation from `10.103.50.0/24` + an LB virtual server for it.
  3. Prove it: `Test-NetConnection <that 10.103.50.x> -Port 6443` → `True` from the jumphost. **Record the actual IP — may not be `.5` this time.**
  4. If all hit → repoint DNS `dc3-supervisor-api.humbledgeeks.com` → the real address, assign **"Kubernetes Service Content Library"** to the Supervisor (needed for VKr/guest clusters), then resume the VKS build (CAPI `Cluster` manifest `vks-doom-cl01`, Steps 8–12) + Kubedoom. If stalled with no External IP → run **Plan B** on `dc3-zone1-supervisor-mgmt`.

### Prior Session Work (Session 2026-06-28)

- **VCF Active Directory SSO post (ID 2199, draft).** Image-heavy how-to (61 screenshots, no diagrams). Source of truth `vcf-license/vcf-active-directory-sso.md`; built via `vcf-license/build_ad_sso_draft.py` (separate media cache `.wp-media-ad-sso-map.json`). Intro was enhanced to tie back to the licensing post. **⚠️ Redaction pending before going live:** the post's own redaction blockquote lists what to blur — `humbledgeeks.com` + host FQDNs, `svc_vcf_sso` DN, `allen@humbledgeeks.com`, the local `admin` account, masked passwords (broker self-signed cert warning is expected, leave it). `[link to your next topic]` placeholder intact. Two pipeline notes: publish.py drops raw HTML comments, so the `<!-- DRAFT NOTES -->` block was re-injected as a `wp:html` Custom HTML block via REST after publish (re-do this on every re-publish); and fenced code inside a `>` blockquote doesn't convert, so the LDAPS sidebar's two PowerShell snippets were lifted to top-level code blocks (Allen approved). See [[blog-publish-flexpod-pattern]].

### Prior Session Work (2026-06-27)

- **VCAP Storage pass post (ID 2079, draft).** Celebratory milestone post. Source: `blog-posts/zero-to-vcap-vcap-storage-pass.md` + LinkedIn companion `…-pass.linkedin.md` (hashtags live in the LinkedIn file, never the blog `.md`). Text-only — 3 `<!-- IMAGE PLACEHOLDER -->` spots await a score screenshot / lab shot / PASS badge.
- **FlexPod VCF 9.1 licensing post (ID 2125, draft).** Image-heavy how-to (43 images: 39 screenshots + 4 PNG diagrams). Built from `vcf-license/zero-to-vcap-flexpod-vcf91-licensing.md` (the "final"; source of truth is `vcf-license/how-to-license-vcf-9.1.md`) via `vcf-license/build_wp_draft.py`. **⚠️ Redaction pending before going live:** screenshots `08`, `10`, `25`, `26`, `27`, `28`, `29` may expose activation code / tenant / Site ID / instance ID / license-server name / host FQDNs — blur before publishing. `[link to your next topic]` placeholder still in the wrap-up.

### Companion Repo

The PowerShell automation scripts and blog post draft for the FlexPod post live in:
`infra-automation/Cisco/UCS/PowerShell/HumbledGeeks/`

### What's Next

- **Publish the VKS/DOOM post (#9, `vcf-vks/vcf-vks-kubernetes-doom.md`)** — redact the screenshots, fill the `[link to your next topic]` placeholder, then push to WordPress (no post ID yet; image-heavy publish pattern). Full TODO is in the END-OF-DAY UPDATE above.
- Decide the next Zero to VCAP topic and fill the `[link to your next topic]` placeholder in post 2125.
- Finish/redact images on the two drafts (2079, 2125), then publish.
- Ongoing study notes, HOL labs, and exam prep content.
- **Publish a simple text post:** `source .venv/bin/activate && python scripts/publish.py blog-posts/<filename>.md --no-images`
- **Publish/update an image-heavy post** (see `vcf-license/build_wp_draft.py`): run the build script, then `python scripts/publish.py vcf-license/_build-wp-draft.md --no-images --post-id <id>`.
- **After EVERY image-heavy (re)publish, run the post-process step** — `publish.py` emits Gutenberg blocks the editor rejects ("Attempt Block Recovery") and drops HTML comments, so re-apply the fixes idempotently: `python vcf-license/postprocess_wp.py <post_id> [--cache <build-media-map.json>] [--src <source.md>]`. For the AD-SSO post the defaults work: `python vcf-license/postprocess_wp.py 2199`. It re-adds image `id`+`wp-image-<id>` class, strips the invalid code-block `language` attr/class, and re-injects the `<!-- DRAFT NOTES -->` wp:html block.

### WordPress Access

- REST API base: `https://humbledgeeks.com/wp-json/wp/v2/`
- Credentials: stored in `.env` (never commit — see `.env.example`)
- Post IDs: FlexPod automation **1794** · VCAP Storage pass **2079** · FlexPod licensing **2125** · AD SSO **2199** · VKS/DOOM **2256** · VVF vCenter patch **2567** · VCF 9.1 Lifecycle **2595** (all live)
- **Publishing gotchas learned 2026-07-19:** (1) `publish.py` resets `featured_media` to 0 on every run, so re-set the featured image after any republish. (2) Re-uploading a changed image under the same filename reuses the URL and Cloudflare keeps serving the stale copy; bump a version marker in the filename instead (see `VCF-9.1-Lifecycle-Upgrades/build_wp_draft.py`). (3) The site 403s scripted requests, so live pages cannot be verified programmatically; check rendering in a browser.

### Theme / Syntax Highlighting

- Active theme: **Astra Child** (`wp-content/themes/astra-child/`)
- Prism.js 1.29.0 loaded globally via `functions.php` — no need to inject scripts into post content
- Post title font override: `.entry-title { font-size: 2.6rem; font-weight: 700; line-height: 1.25; }` (in Astra Customizer → Additional CSS)

---

## 🎯 Certification Goal

- **Exam**: VCAP-VCF Administrator Certification (Broadcom Knight Journey)
- **Goal**: Get nominated as a Broadcom VMware Knight
- **Timeline**: 6–7 month structured study plan beginning February 2026
- **Approach**: Hands-on labs, weekly blog posts, LinkedIn posts, and exam blueprint alignment

---

## 👤 About Allen

- Works as a Modern Infrastructure Solutions Architect at a VAR/MSP environment
- Daily exposure to NetApp ONTAP, VMware vSphere/vCenter/NSX/vSAN, Cisco UCS, and AWS
- MacBook-based development environment with VS Code, GitHub CLI, PowerShell, and Ansible
- Active member of the VMUG community
- Runs HumbledGeeks.com — a technical blog focused on real-world learning journeys

### Owner / Social

- **GitHub**: humbledgeeks-allen
- **Org**: humbledgeeks
- **Blog**: HumbledGeeks.com
- **Twitter/X**: @humbledgeeks

---

## 📝 Blog Series: Zero to VCAP

- Published weekly on HumbledGeeks.com
- **Tone**: Honest, relatable, and educational — written for fellow practitioners, not executives
- **Format**: Narrative-driven with practical takeaways, lab tips, and resource links
- **Length**: 800–1500 words per post
- **Goal**: Document the full cert journey from start to passing, mistakes included
- Use markdown formatting compatible with HumbledGeeks.com
- Write in first person, conversational tone
- Target audience: VMware admins transitioning to VCF
- Include practical lab examples where possible

---

## 🛠️ Technical Environment

- VMware Hands-On Labs (HOL) — primary lab environment
- Access to physical hardware in his own lab
- ESXi deployments and VCF preparation labs
- vCenter, NSX, vSAN, VCF components (SDDC Manager)
- PowerShell and Ansible automation scripts (hosted on GitHub)

---

## 📁 Folder Structure

- `blog-posts/` — Draft blog posts in Markdown for HumbledGeeks.com
- `study-notes/` — Study notes, summaries, and key concepts
- `lab-configs/` — Lab configurations, screenshots, and diagrams
- `resources/` — Links, references, and study materials

---

## 🔬 Study Focus Areas

- VMware Cloud Foundation (VCF) architecture
- ESXi hardening and configuration
- vCenter, vSAN, NSX administration
- SDDC Manager
- VMware Hands-On Labs (HOL)

---

## 💡 How to Help

- **Study sessions**: Help Allen work through exam blueprint objectives with explanations, analogies, and quizzes
- **Blog drafts**: Help write or refine weekly blog posts in Allen's authentic voice — clear, humble, and technically accurate
- **Lab guidance**: Suggest HOL labs, troubleshoot lab scenarios, explain concepts
- **Exam prep**: Create practice questions, flashcards, and objective-by-objective breakdowns
- **ESXi/VCF hardening**: Help document and refine automation scripts

---

## 📌 Preferences

- Keep technical explanations grounded in real-world scenarios Allen would encounter on the job
- Blog content should sound like Allen wrote it — not overly polished or corporate
- Flag when something has changed post-Broadcom acquisition vs. legacy VMware documentation
- When in doubt, ask before assuming — Allen's environment has specific constraints
