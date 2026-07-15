# Publish steps — "VCF vs. VVF" post (image-heavy pattern)

Run these from the repo root in VS Code, with the venv active. This creates a
**draft** on humbledgeeks.com (never publishes live — `status: draft`).

Source of truth: `blog-posts/zero-to-vcap-vcf-vs-vvf.md`
Diagrams: `blog-posts/images/*.png` (4, rendered 2x from the original SVGs)

## Prep already done (no action needed)
- 4 SVG diagrams rendered to PNG in `blog-posts/images/`.
- Image refs in the `.md` point at those PNGs.
- Blank line inserted between each image and its italic caption, so each image
  becomes its own Gutenberg `wp:image` block (verified: 4 standalone blocks, 0 fused).
- 10 links added — 4 internal series links + 6 external. See "Links added" below.
- No sensitive data to redact (no IPs / UPNs / FQDNs in the body or the diagrams).

## 1. Activate the venv
```bash
cd ~/_github/zero-to-vcap
source .venv/bin/activate
```

## 2. Build — upload the 4 PNGs to WP media + rewrite refs to URLs
```bash
python blog-posts/build_vcf_vs_vvf_draft.py
```
Writes `blog-posts/_build-vcf-vs-vvf-draft.md` and caches the media map at
`blog-posts/.wp-media-vcf-vs-vvf-map.json`. Re-runs reuse already-uploaded media.

## 3. Create the draft
```bash
python scripts/publish.py blog-posts/_build-vcf-vs-vvf-draft.md \
  --no-images --tags "VVF,vSphere Foundation,Migration,vMotion,Workload Domain"
```
`--no-images` is required (it skips DALL-E; your diagrams are already embedded).
Copy the **Post ID** it prints.

## 4. Post-process (canonical image blocks)
`publish.py` emits image blocks the editor flags with "Attempt Block Recovery",
so re-apply the fix. This post has no code blocks and no DRAFT NOTES, so `--src /dev/null`:
```bash
python vcf-license/postprocess_wp.py <POST_ID> \
  --cache blog-posts/.wp-media-vcf-vs-vvf-map.json --src /dev/null
```
Re-run steps 3 + 4 (with the same Post ID, adding `--post-id <POST_ID>` to step 3)
after any later edit to the source `.md`.

## 5. Eyeball in the WP editor
- 4 diagrams render, each above its caption, with sensible spacing.
- Featured image is empty (text/diagram post) — set one if you want.
- Fill the intro/series cross-links if any prior post IDs changed.

## Links added (anchor -> URL)
Internal (series):
- "from physical hosts and a blank canvas" -> FlexPod VCF foundation (1794)
- "integrated Active Directory" -> AD SSO post (2199)
- "VMware Kubernetes Service" -> VKS/DOOM post (2256)
- "licensing article" -> FlexPod licensing post (2125)

External (verified July 2026):
- "KubeDOOM" -> https://github.com/storax/kubedoom
- "VMware vSphere Foundation" -> https://www.vmware.com/products/cloud-infrastructure/vsphere-foundation
- "VMware Cloud Foundation" -> https://www.vmware.com/products/cloud-infrastructure/vmware-cloud-foundation
- "cross-vCenter vMotion" -> Broadcom TechDocs (vSphere 9.1 migration)
- "upgrade path" -> VMware VCF 9.1 feature comparison & upgrade paths
- "VCF Upgrade Planning Tool" -> https://vmware.github.io/vcf-upgrade-planner/ (was already in the post)
