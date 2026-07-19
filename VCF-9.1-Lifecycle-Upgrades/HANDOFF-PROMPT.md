You are my blog-publishing assistant for the HumbledGeeks.com "Zero to VCAP" series, working in my `zero-to-vcap` repo in VS Code. Read `CLAUDE.md` at the repo root first for series voice, the WordPress REST setup, and the image-heavy publish pattern. Then help me finish and publish one specific post.

## The post
- Working folder: `VCF-9.1-Lifecycle-Upgrades/`
- Draft (source of truth for prose): `VCF-9.1-Lifecycle-Upgrades/draft/zero-to-vcap-vcf91-lifecycle-upgrades.md`
- Technical source notes: `VCF-9.1-Lifecycle-Upgrades/SOURCE-NOTES.md`
- Image disposition + sensitive-data findings: `VCF-9.1-Lifecycle-Upgrades/IMAGE-MANIFEST.md`
- Rendered Word preview (reference only, not a publish artifact): `VCF-9.1-Lifecycle-Upgrades/zero-to-vcap-vcf91-lifecycle-upgrades-PREVIEW.docx`
- Title: "VCF 9.1 Lifecycle: One Control Plane, and the Real Work to Get There"
- Angle: how lifecycle actually works in VCF 9.1 vs the 8.0 U3 / 5.x two-tool model. Steady state is simpler; getting to 9.1 is a real project. Not a troubleshooting post.

## Current state (already done, do not redo)
- Draft is written and passes the voice rules below. ~2,500 words.
- 17 screenshots are placed and captioned across `images/01-old-way` through `images/05-depot-binaries`. Raw dump of all 56 stays in `images/_inbox/`.
- Image links in the draft use `../images/NN-folder/upgrade_X.jpg` because the markdown lives in `draft/`.
- Security: `images/_inbox/upgrade_24.jpg` had a cleartext VCF Operations admin password. It is now redacted and cropped. It is NOT used in the post.

## Hard rules (do not violate)
- First person, engineer to engineer. Match my voice in the other posts under `blog-posts/` and the folder posts.
- NO em dashes anywhere. Use commas, periods, or restructure.
- Short paragraphs, two to four sentences. No marketing words (no "seamless," "leverage," "empower," "journey," "game changer," "revolutionary").
- Never delete my lines or comments from source files. Do not renumber or reorder my content without asking.
- Do not publish live until the security and redaction items below are cleared.

## Tasks, in order
1. Sanity-check the draft renders on WordPress with the `../images/NN/` relative paths. My existing build scripts (see `vvf-vcenter-upgrade/build_wp_draft.py` and `vcf-license/build_wp_draft.py`) assume the markdown and `images/` sit in the same directory and reference `images/upgrade_X.jpg`. This post has the markdown in `draft/` and images in `../images/NN/`. Create a build script for THIS post (copy `vvf-vcenter-upgrade/build_wp_draft.py`, adapt it) that: resolves `../images/NN-folder/` paths, uploads each image to WordPress media once, rewrites the built markdown to the canonical WP URLs, and uses its OWN media cache file `VCF-9.1-Lifecycle-Upgrades/.wp-media-vcf91-lifecycle-map.json`. Emit the built file as `VCF-9.1-Lifecycle-Upgrades/_build-wp-draft.md`.
2. Push as a NEW WordPress DRAFT (no post ID yet). Follow the image-heavy pattern from `CLAUDE.md`: run the new build script, then `python scripts/publish.py VCF-9.1-Lifecycle-Upgrades/_build-wp-draft.md --no-images`, capture the new post ID it returns.
3. Run the post-process step against the new post ID: `python vcf-license/postprocess_wp.py <new_post_id> --cache VCF-9.1-Lifecycle-Upgrades/.wp-media-vcf91-lifecycle-map.json --src VCF-9.1-Lifecycle-Upgrades/draft/zero-to-vcap-vcf91-lifecycle-upgrades.md`. Confirm every image is canonical and no Gutenberg "Attempt Block Recovery" blocks remain.
4. Suggested tags: VCF, VMware Cloud Foundation, 9.1, Lifecycle Management, Upgrade, Fleet Lifecycle, SDDC Lifecycle, VCF Operations, SDDC Manager, Aria Suite Lifecycle, Zero to VCAP.
5. Update the "Published Blog Posts" table and the "WordPress Access" post-ID list in `CLAUDE.md` with this post's new ID once it exists.

## Decisions I still owe you (ask me, do not guess)
- COMPANION LINK: the draft links the VVF vCenter post as `https://humbledgeeks.com/?p=2567` (draft ID 2567). When that post publishes with a real slug, swap this to the final URL. Ask me if it is live yet.
- REDACTION: the 17 used shots show `dc3-*.humbledgeeks.com` FQDNs, `10.103.x` IPs, and in the Tasks views the `admin.allen@humbledgeeks.com` UPN and `administrator@vsphere.local`. In the VKS post I redacted these; in the VVF post I left lab names visible. Ask me which way to go for THIS post before publishing, and if redacting, blur those in the placed shots (see `IMAGE-MANIFEST.md` for exact values and files).
- SECURITY: I need to rotate the VCF Operations admin password that was exposed in `upgrade_24.jpg` (now redacted). Remind me. Decide whether to keep `upgrade_24.jpg` in the repo at all; it is unused.

## Known gaps to note in the post or a follow-up
- The core-components section (Section 5) has only a precheck shot (`upgrade_32`). No Plan Component Upgrade wizard, Submit Plan, or Start Now captures exist. Either leave the section as-is or I will grab those on my next core upgrade.
- There is a teased follow-up on the VCF 9.1.0.0 known issue where fleet lifecycle sub-tasks show In Progress after a workflow completes. Keep the callout in this post short; the detail goes in the follow-up.
