# LinkedIn post — VCF 9.1 deployment walkthrough

> Blog link below only goes live AFTER the WordPress draft (post ID 1949) is published.
> Public URL: https://humbledgeeks.com/zero-to-vcap-deploying-vmware-cloud-foundation-91-screen-by-screen/

---

I just deployed VMware Cloud Foundation 9.1 from bare metal in my lab — and documented every single screen so you don't have to guess.

It's the latest stop on my Zero to VCAP journey: standing up the VCF 9.1 management domain, end to end, with all 71 screenshots.

A few honest takeaways coming from 9.0.2:

✅ The new Deployment Wizard feels like a different product — a guided Plan → Prepare → Deploy flow, FQDN pre-fill, and validation that catches DNS and certificate problems BEFORE you waste an hour on a doomed deployment.

⏳ It takes almost 2x longer to deploy than 9.0.2. There's just more being built — VCF Operations, VCF Automation, and the whole fleet management plane on top of vCenter, NSX, and SDDC Manager.

💾 9.1 is resource-hungry. My four hosts couldn't clear the recommended buffer at HA/Medium, so I right-sized to Simple/Small. Lesson: size your hardware to the deployment model you actually want — not the other way around.

🔐 I hardened my ESXi hosts and regenerated their certificates up front (with my own PowerShell scripts) so they sailed through host validation instead of failing mid-deploy.

🗄️ Storage landed on my Cisco UCS FlexPod with NetApp ASA A30 over Fibre Channel — no vSAN required.

And the headline if you're still on vSphere: you may NOT have to rebuild. VCF 9.1 supports converging an existing vSphere 8.0 U3a+ environment into the fleet — a genuine upgrade path.

Full screen-by-screen walkthrough here 👇
https://humbledgeeks.com/zero-to-vcap-deploying-vmware-cloud-foundation-91-screen-by-screen/

Next in the series: building a workload domain, licensing the environment, and converging my existing vCenter 8.0 U3 lab. Follow along if you're on the same path.

#VMware #VMwareCloudFoundation #VCF #Broadcom #vSphere #VCAP #ESXi #NSX #FlexPod #NetApp #HomeLab #PrivateCloud
