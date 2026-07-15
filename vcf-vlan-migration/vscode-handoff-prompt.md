# VS Code handoff prompt

Copy everything in the fenced block below into a new Claude session in VS Code (repo root
`zero-to-vcap`). It has the CLAUDE.md pipeline context, so it can finish and publish.

```
You are my Zero to VCAP blog assistant working in the zero-to-vcap repo. Follow CLAUDE.md.

STATUS: The post is already fully drafted and saved at
vcf-vlan-migration/vcf-vlan18-legacy-vlan-on-wld.md
Title: "Several Roads out of 8.0U3: Cross-vCenter vMotion onto VCF 9.1", front matter draft: true.
Do NOT rewrite it from scratch. It is complete prose. Your job is to finish and publish it.

VOICE RULES (hard): first person, engineer to engineer, honest about wrong turns,
NO em dashes anywhere, no marketing language, short WordPress-friendly paragraphs,
CLI in code blocks. Do not claim VCF "approved" the out-of-band NSX change. Do not
present the NFC disk-path stack selection as a universal law.

IMAGES:
- Build/validation screenshots (already renamed and in place): vcf-vlan-migration/vlan-images/vlan-01..40-*.jpg
- The post references 24 of them inline; the rest are spares in the same folder.
- The cross-vCenter vMotion screenshots are referenced as move-01..move-19 in vlan-images/
  and still need to be SAVED into that folder from my pasted images. Filenames and what each shows:
    move-01-host-import-vms.jpg          host esxi05 Actions menu, Import VMs
    move-02-source-vcenter-creds.jpg     source vCenter dc3-hst-mgmt1, username admin.allen
    move-03-security-alert-cert.jpg      certificate Security Alert, YES
    move-04-source-vcenter-connected.jpg "Successfully connected to dc3-hst-mgmt1"
    move-05-select-rhel9-poweredon.jpg   Import VMs list, dc3-hst-rhel9 checked, Powered On
    move-06-compute-evc-error.jpg        compute step EVC / hardware error (KB 1003212, MDS_NO)
    move-07-shutdown-guest-os.jpg        Actions > Power > Shut Down Guest OS
    move-08-guest-poweroff-complete.jpg  rhel9 Powered Off, guest shutdown task completed
    move-09-select-rhel9-poweredoff.jpg  Import VMs list, rhel9 checked, Powered Off
    move-10-compute-compat-success.jpg   compute step "Compatibility checks succeeded"
    move-11-storage-vmfs01.jpg           storage VMFS01, Same format as source
    move-12-select-folder.jpg            folder Discovered virtual machine, checks succeeded
    move-13-select-network-picker.jpg    Select Network dialog, Networks tab, seg-vlan18-apps
    move-14-network-mapping-kb56991.jpg  dc3-app (vSAN) mapped to seg-vlan18-apps, KB 56991 warning
    move-15-ready-to-complete-finish.jpg Ready to complete summary, Finish
    move-16-relocate-task.jpg            Relocate virtual machine task at 63%
    move-17-landed-poweredoff.jpg        rhel9 on WLD powered off, VMFS01 + seg-vlan18-apps
    move-18-poweredon-summary-ip.jpg     rhel9 powered on, IP 10.103.18.180, host esxi08
    move-19-guest-ping-gateway.jpg       RHEL 9 console, ping 10.103.18.1 succeeds

TASKS, in order:
1. Confirm all move-01..19 image files exist in vcf-vlan-migration/vlan-images/. List any missing so I can add them.
2. REDACTION pass before publish. These screenshots and the body expose values to blur/scrub:
   host FQDNs (*.humbledgeeks.com), the usernames admin.allen@humbledgeeks.com and
   Administrator@vsphere.local, the SHA-256 certificate fingerprint, the webconsole URL serverGuid,
   and IPs (10.103.16.x, 10.103.17.x, 10.103.18.180, 10.103.50.x if present). Tell me exactly which
   images need blurring and where; do not auto-delete anything.
3. Fill the "[link to your next topic]" placeholder at the end. The next post is a VVF in-place
   upgrade of the production 8.0U3 environment, so tease that.
4. Publish as an image-heavy post per CLAUDE.md: build script -> publish.py --no-images -> postprocess_wp.py.
   Assign a post ID, keep draft on WordPress until I approve, and report the WP draft URL.

Start by reading vcf-vlan18-legacy-vlan-on-wld.md and vmotion-capture-worklist.md, then do step 1.
```
