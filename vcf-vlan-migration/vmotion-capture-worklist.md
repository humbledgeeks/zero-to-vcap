# Cross-vCenter vMotion: Run + Capture Worklist (dc3)

Working checklist for performing the Advanced Cross vCenter vMotion PoC and capturing
the screenshots that slot into `vcf-vlan18-legacy-vlan-on-wld.md`. Filenames below match
the `move-0N` placeholders already wired into the post. Drop the captures into
`vlan-images/` with these exact names and they render automatically.

Entry-point note: this is Advanced Cross vCenter vMotion, driven from the destination
vCenter with the Import VMs workflow (no shared SSO, no linked mode required). The exact
right-click label and wizard panel order can vary slightly by build. Verify the label on
your `dc3-vc02` console before trusting the click path below. The field logic does not
change even if the entry point sits somewhere slightly different.

## 0. Before you start (decisions, not screenshots)

- Pick the PoC VM on VLAN 18 and write down its name and current IP.
- Confirm `VMFS01` (A30 FC) is mounted on the WLD hosts and has capacity.
- Decide the disk format up front: Thin, or Thick Provision Eager Zeroed. Do NOT accept
  the Thick Provision Lazy Zeroed default this A30 showed earlier.
- To bypass EVC / CPU-compat, and for the AD DC leg: shut the guest down cleanly so this
  is a cold relocate. Do NOT let the wizard upgrade the VM hardware version.

## 1. Prove both network paths first (run and capture before the move)

Two independent paths. Run each from the ESXi shell (SSH) on the hosts. Screenshot the
output. A shared physical switch does not prove either path.

Capture `move-vmkping-jumbo` (Path one, vMotion stack, jumbo, both directions):

```
vmkping -S vmotion -d -s 8972 <destination WLD vMotion IP>
```

Then run the reverse from a WLD host back to the legacy vMotion IP `10.103.17.75`.
Shoot the output showing 0% packet loss. The `-d -s 8972` proves MTU 9000 end to end,
because an 8972-byte don't-fragment packet cannot complete across a 1500 hop.

Capture `move-vmkping-mgmt` (Path two, NFC disk copy, management stack, both directions):

```
vmkping <destination management IP>
```

NFC uses the Provisioning stack if one exists and falls back to Management if not. On
this build there is no Provisioning stack, so it rides Management. Confirm that on yours
and test whichever stack NFC actually uses. Shoot the output both directions.

(These two are not yet referenced in the post. Tell me if you want image slots added to
the "two vMotion network paths" section and I will wire them in.)

## 2. The move: Import VMs wizard, run from destination dc3-vc02

Right-click the destination cluster `dc3-wld-cl01` in `dc3-vc02` and choose Import VMs.

| Capture file | Wizard step | What to click / confirm | What the shot must show |
|---|---|---|---|
| `move-01-import-vms-launch.jpg` | Launch | Right-click `dc3-wld-cl01` > Import VMs | Wizard open, targeting `dc3-wld-cl01` |
| `move-02-source-vcenter-added.jpg` | Source vCenter | Enter `dc3-hst-mgmt1.humbledgeeks.com`, creds, accept thumbprint | Source vCenter added / thumbprint accept dialog |
| `move-03-source-vm-selected.jpg` | Select VMs | Pick the PoC VM from legacy `h610c` inventory | The VM checked/selected |
| `move-04-destination-compute.jpg` | Compute | Cluster `dc3-wld-cl01` and target folder | Destination compute chosen, compatibility green |
| `move-05-destination-storage-diskformat.jpg` | Storage | Datastore `VMFS01`, set disk format explicitly | Datastore `VMFS01` and the disk-format dropdown set (not Thick Lazy) |
| `move-06-network-mapping.jpg` | Networks | Map source VLAN 18 port group to `seg-vlan18-apps` | The mapping row: source PG on the left, `seg-vlan18-apps` on the right |
| `move-07-relocate-task.jpg` | Finish | Review, Finish, then watch Recent Tasks | Relocate virtual machine task at or near 100%, ideally both vCenters |
| `move-08-post-move-validation.jpg` | Validate | VM powered on, guest IP intact | VM summary on a `dc3-wld-cl01` host + a guest `ip a` / `ipconfig` showing the same `10.103.18.x` |

## 3. Post-move validation (what move-08 has to prove)

- Running on a `dc3-wld-cl01` host in `dc3-vc02`.
- Guest still holds its original `10.103.18.x` address, pings `10.103.18.1`, routes out.
- On datastore `VMFS01`, connected to the `seg-vlan18-apps` DVPG.
- Windows DC only: same NIC adapter with no hidden ghost, static IP intact, AD services
  healthy. Confirm no hardware-version upgrade happened.

## 4. Shoot these too if they happen

- If a powered-on (live) move balks on 8.0U3 to 9.x CPU compatibility, fall back to a cold
  move for the PoC and capture the compatibility message. That message is a good addition
  to the EVC section of the post.
- If the Relocate task stalls, re-run both path proofs from section 1 before anything else.

## Naming reminder

Build set (already in the post): `vlan-01` through `vlan-40` in `vlan-images/`.
Move set (this run): `move-01` through `move-08`, plus the two optional `move-vmkping-*`
shots. Keep them in `vlan-images/` so nothing collides with the build set.
