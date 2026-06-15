# LinkedIn post — VCF 9.1 vSphere Supervisor wall / NSX edge spine

> Blog link below only goes live AFTER the WordPress draft (post ID 2030) is published.
> Public URL (from slug): https://humbledgeeks.com/zero-to-vcap-when-vsphere-supervisor-hit-a-wall-building-an-nsx-edge-spine-in-vcf-91/
> After publishing, swap in your lnkd.in short link like the last post.

---

🚀 Another Stop on My Zero to VCAP Journey — and This One Fought Back 🚀

I set out to deploy a VMware Cloud Foundation 9.1 workload domain with vSphere Supervisor (vSphere Kubernetes) enabled… and the wizard stopped me cold at the very last step. The "VPC Connectivity Profile" dropdown was empty. No profile, no Supervisor, no finishing the deploy.

So I did what I always do: documented every single screen of the fix so you don't have to guess. This is the latest stop on my Zero to VCAP journey — a multi-day, screen-by-screen teardown of why a shared-NSX workload domain has no Supervisor networking spine, and how I built one from scratch.

A few honest lessons learned:

Sharing an NSX instance does NOT hand you a usable Supervisor networking stack. You inherit transport nodes and overlay segments, but the north-south spine — an NSX Edge cluster, a Tier-0 gateway, and IP blocks — doesn't exist yet. That empty dropdown isn't a bug; it's the wizard telling you the spine hasn't been built.

The wall went deeper than NSX. The overlay needs jumbo frames end to end, and my Meraki MX was routing every TEP VLAN at 1500 MTU. The real fix lived a layer down — moving the L3 gateways onto the switch stack at 9578 so jumbo is true on the wire before NSX will even pass its Run Check.

The guided edge wizard has traps. It collapses the edge TEP onto the host VLAN, BGP defaults to On, the VPC IP-block fields are lookups (not free-text), and the private Transit Gateway block MUST be a /16 — a /24 silently fails Supervisor provisioning later.

And the wizard doesn't finish the job. The Tier-0 default route, the HA VIP, and outbound SNAT are all post-deploy steps you set by hand in NSX Manager.

As I've said before, I firmly believe in teaching people how to fish. The wins are easy to post about — but the walls, the detours, and the "why is this dropdown empty" moments are where the real learning happens. If my struggle saves you a multi-day one, it was worth writing down.

Building a home lab to follow along? A VMUG Advantage membership is how a lot of us get the VCF bits for personal-use labs (plus a discount on the certification exam).

Full screen-by-screen walkthrough:
https://lnkd.in/REPLACE_AFTER_PUBLISH

Next up:
➡️ Finishing the vSphere Supervisor enablement now that the profile exists
➡️ Licensing the environment across the fleet
➡️ Proving lifecycle updates through SDDC Manager

If you're chasing VCAP, running vSphere Supervisor, or building your own home lab, I'd love to hear how your journey is going.

#VMware #VMwareCloudFoundation #VCF #VCF91 #Broadcom #NSX #vSphere #vSphereSupervisor #Kubernetes #VCAP #ZeroToVCAP #VMUG #NetApp #FlexPod #HomeLab #PrivateCloud
VMware User Group (VMUG) · Broadcom · VMware Cloud Foundation (VCF)
