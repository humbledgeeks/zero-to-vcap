# Connecting My FlexPod VCF 9.1 Deployment to Active Directory (VCF Single Sign-On)

In the last post I took my FlexPod VCF 9.1 environment from evaluation to fully
licensed. The platform was legitimate — but it still didn't know who anyone was.

Every login was a local `@vsphere.local` account. That's fine on day one, but it
doesn't scale past a handful of admins, it leaves no real audit trail, and it's
the first thing a security review flags. Shared local credentials are technical
debt you feel the moment a second person needs access — and in a VCF environment
that's going to grow, "the moment" comes fast.

So in this post I wire [VMware Cloud Foundation 9.1](https://www.vmware.com/products/cloud-infrastructure/vmware-cloud-foundation)
into my **humbledgeeks.com** [Active Directory](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview)
using [**VCF Single Sign-On**](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-0/fleet-management/what-is/setting-up-sso.html)
over **LDAPS** — administrators sign in with their own AD credentials, and access
is driven entirely by AD group membership instead of by who happens to know a
local password.

This runs on a [**FlexPod**](https://www.cisco.com/site/us/en/solutions/computing/converged-infrastructure/flexpod/index.html) — Cisco UCS compute, NetApp ASA30 storage — with VCF
9.1, a management domain (`dc3-vc01`), a workload domain (`dc3-vc02` / `dc3-wld01`),
and NSX (`dc3-nsx01`). It's the foundational step that makes clean role-based
access control possible for everything that follows in this series — which is
exactly why it's worth doing carefully, and in order.

---

## How identity works in VCF 9.x (read this first)

VCF 9 replaced the old per-vCenter SSO model with **VCF Single Sign-On**, brokered
centrally by the **VCF Identity Broker** and configured from one place:
**VCF Operations → Manage → Identity and Access**.

Three concepts to hold onto before you start:

- **Identity is configured centrally now.** Once SSO is enabled, you no longer set
  identity sources directly in each vCenter — VCF Operations owns it and
  *overrides* the vCenter's existing identity configuration.
- **The Identity Broker has two deployment modes.** **Instance** is a dedicated,
  standalone broker (multi-node capable); **Embedded** runs single-node inside the
  management-domain vCenter. My environment already runs an Instance broker,
  `dc3-vidb.humbledgeeks.com`, so this post *reuses* it rather than deploying one.
- **Provisioning a group ≠ granting access.** Syncing an AD group only makes it
  *available* to assign roles to. Access is granted entirely by role assignment.

The whole thing is a guided four-step **Configure VCF SSO** wizard — deployment
mode, identity provider, enable SSO for vCenter/NSX, assign VCF roles — followed by
joining the management appliances and verifying.

---

## Prerequisites (validate, don't assume)

1. **[LDAPS](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/enable-ldap-over-ssl-3rd-certification-authority) enabled on the domain controllers.** VCF needs the **root CA in PEM** to
   trust the DCs. You do *not* need a public CA — an internal AD Certificate
   Services role or even a self-signed DC certificate works. Validate first (see
   sidebar). In my lab, LDAPS is confirmed on `dc3-srv-core01` and
   `dc3-srv-core02`, both chaining to `CN=HumbledGeeks-Root-CA`.
2. **Enhanced Linked Mode (ELM) must be OFF.** VCF SSO is incompatible with ELM —
   the enable screen only lists vCenters/NSX that are *not* in an ELM ring, so it's
   self-enforcing.
3. **Admin with the "All Objects" scope** in VCF Operations (Administration →
   Control Panel → Access Control).
4. **A dedicated, read-only AD bind account** (Step 0).
5. **Healthy DNS and time** between VCF and the DCs.

> **Sidebar — validate LDAPS and export the root CA (PowerShell).**
> Find your real DC name first (`$env:LOGONSERVER` or `nltest /dclist:<domain>`),
> then test the bind:

```powershell
Add-Type -AssemblyName System.DirectoryServices.Protocols
$dc = "dc3-srv-core01.humbledgeeks.com"
Test-NetConnection $dc -Port 636        # TcpTestSucceeded : True
$c = New-Object System.DirectoryServices.Protocols.LdapConnection("$($dc):636")
$c.SessionOptions.SecureSocketLayer = $true
$c.SessionOptions.ProtocolVersion  = 3
$c.Bind(); "LDAPS bind OK"
```

> Export the root CA the DC presents (this is the PEM you upload to VCF):

```powershell
$tcp = New-Object System.Net.Sockets.TcpClient($dc,636)
$ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(),$false,({$true}))
$ssl.AuthenticateAsClient($dc)
$leaf  = [System.Security.Cryptography.X509Certificates.X509Certificate2]$ssl.RemoteCertificate
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.Build($leaf) | Out-Null
$pem=""; for($i=1;$i -lt $chain.ChainElements.Count;$i++){$x=$chain.ChainElements[$i].Certificate;$pem+="-----BEGIN CERTIFICATE-----`n"+[Convert]::ToBase64String($x.RawData,'InsertLineBreaks')+"`n-----END CERTIFICATE-----`n"}
$pem | Out-File -Encoding ascii "$env:USERPROFILE\Desktop\humbledgeeks-ca-chain.pem"
```

> A single certificate in the file = single-tier PKI (the root issues DC certs
> directly), and that one PEM covers every DC.

---

## What you'll need on hand (this environment's values)

| Field | Value |
|---|---|
| Directory display name | `humbledgeeks` |
| Base DN | `DC=humbledgeeks,DC=com` |
| Primary DC | `ldaps://dc3-srv-core01.humbledgeeks.com:636` |
| Secondary DC | `ldaps://dc3-srv-core02.humbledgeeks.com:636` |
| Root CA (PEM) | `humbledgeeks-ca-chain.pem` (covers both DCs) |
| Search attribute | `sAMAccountName` |
| Bind account (DN) | `CN=svc_vcf_sso,OU=Service,OU=HG_Accounts,DC=humbledgeeks,DC=com` |
| Base group DN | `OU=VMware,OU=Technologies,OU=HG_Accounts,DC=humbledgeeks,DC=com` |
| Identity Broker | `dc3-vidb.humbledgeeks.com` (Instance mode, already deployed) |

---

## Step 0 — Create the read-only AD bind account

Create a dedicated service account so the LDAP bind is least-privilege and
auditable — don't reuse a product service account.

```powershell
Import-Module ActiveDirectory
$pw = Read-Host "Password for svc_vcf_sso" -AsSecureString
New-ADUser -Name "svc_vcf_sso" -SamAccountName "svc_vcf_sso" `
  -UserPrincipalName "svc_vcf_sso@humbledgeeks.com" `
  -DisplayName "VCF SSO LDAP Bind (read-only)" `
  -Description "Read-only bind account for VCF Single Sign-On (AD/LDAP)" `
  -Path "OU=Service,OU=HG_Accounts,DC=humbledgeeks,DC=com" `
  -AccountPassword $pw -Enabled $true -PasswordNeverExpires $true -CannotChangePassword $true
```

No elevated group membership is required — standard domain-user read access is
enough for LDAP lookups. Confirm it authenticates over LDAPS before you put it in
the wizard:

```powershell
$cred = New-Object System.Management.Automation.PSCredential("svc_vcf_sso@humbledgeeks.com",$pw)
$c = New-Object System.DirectoryServices.Protocols.LdapConnection("dc3-srv-core01.humbledgeeks.com:636")
$c.SessionOptions.SecureSocketLayer=$true; $c.SessionOptions.ProtocolVersion=3; $c.AuthType="Basic"
$c.Bind($cred.GetNetworkCredential()); "Authenticated LDAPS bind OK"
```

> **Gotcha:** if `New-ADUser` errors on password complexity, it still creates a
> *disabled* account. Fix it with `Set-ADAccountPassword` + `Set-ADUser -Enabled
> $true` rather than trying to recreate it.

---

## Step 1 — Log in and navigate to Identity and Access

Log into VCF Operations. On a fresh environment this is still a **local account**
(`admin`) — exactly what we're about to move away from.

![VCF Operations login page using a local account](https://humbledgeeks.com/wp-content/uploads/2026/06/01-ops-login-1-scaled.jpg)

*Day one: local `admin` login. By the end of this post, AD credentials do the job.*

After login you land on the **Launchpad**, the tile-based home for VCF Operations.

![VCF Operations Launchpad welcome tiles](https://humbledgeeks.com/wp-content/uploads/2026/06/02-launchpad-scaled.jpg)

*The Launchpad — Identity and Access lives under the Manage area.*

From the top navigation, head to **Manage**.

![VCF Operations Home with the Manage menu](https://humbledgeeks.com/wp-content/uploads/2026/06/03-home-manage-menu-scaled.jpg)

*Manage is where Fleet Management — including identity — lives.*

Open **Identity & Access**. The **VCF SSO Overview → Get Started** page lays out
the whole flow as a diagram: deploy/identify a broker, configure the identity
provider, connect components, assign roles, and you have SSO.

![Identity and Access Get Started page with the SSO architecture diagram](https://humbledgeeks.com/wp-content/uploads/2026/06/04-identity-access-getstarted-scaled.jpg)

*The Get Started page maps the journey before you take it.*

Scroll down and click **CONFIGURE SSO** to begin. (Note the "begin with reviewing
the prerequisites" link — we'll do exactly that next.)

![Get Started page with the CONFIGURE SSO button](https://humbledgeeks.com/wp-content/uploads/2026/06/05-getstarted-configure-sso-scaled.jpg)

*CONFIGURE SSO kicks off the guided setup.*

---

## Step 2 — Acknowledge the prerequisites

The **Prerequisites** tab is a five-item acknowledgment gate. Two of these are
real, actionable attestations — **ELM disabled** and the **"All Objects" scope** —
the other three are awareness items (vCenter identity override, SDDC Manager UI
stays local-only, PowerCLI may need re-integration).

![Prerequisites tab with all acknowledgments unchecked](https://humbledgeeks.com/wp-content/uploads/2026/06/06-prerequisites-unchecked-scaled.jpg)

*Read each one — they describe exactly what enabling SSO changes.*

Tick all five (only do so once they're genuinely true for your environment) and
click **SUBMIT**.

![Prerequisites tab with all five acknowledgments checked and SUBMIT active](https://humbledgeeks.com/wp-content/uploads/2026/06/07-prerequisites-checked-scaled.jpg)

*Don't rubber-stamp the ELM box — confirm Enhanced Linked Mode is actually off first.*

---

## Step 3 — Choose the deployment mode (reuse the existing broker)

The **Configure VCF SSO** wizard opens at 0%. Step 1 is **Choose Deployment Mode**.

![Configure VCF SSO wizard at 0 percent](https://humbledgeeks.com/wp-content/uploads/2026/06/08-configure-sso-0pct-scaled.jpg)

*Four steps: deployment mode, identity provider, enable SSO for vCenter/NSX, assign roles.*

Click **START**. You're offered **Instance (Recommended)** versus **Embedded**.
My `dc3-vidb` is a standalone broker, so I choose **Instance**.

![Choose Deployment Mode with the Instance card selected](https://humbledgeeks.com/wp-content/uploads/2026/06/09-deployment-mode-instance-scaled.jpg)

*Instance = dedicated, resilient broker. Embedded would deploy a new single-node broker into the management vCenter.*

Selecting Instance reveals **Choose Identity Broker**, which detects the existing
`dc3-vidb.humbledgeeks.com` for VCF instance `hg-vcf-flexpod`. Leave it selected
and click **CONFIGURE** — no new broker is deployed.

![Choose Identity Broker showing the existing dc3-vidb detected](https://humbledgeeks.com/wp-content/uploads/2026/06/10-deployment-broker-selected-scaled.jpg)

*It found my existing broker — exactly what I wanted. No second appliance.*

Step 1 flips to **Completed** (25%) and **Configure Identity Provider** unlocks.

![Configure VCF SSO at 25 percent, step 1 completed](https://humbledgeeks.com/wp-content/uploads/2026/06/11-configure-sso-25pct-scaled.jpg)

*Deployment mode done. On to the identity provider.*

---

## Step 4 — Choose AD/LDAP as the identity provider

Click **START** on **Configure Identity Provider**. VCF 9.1 supports a long list —
Okta, Ping, Entra ID, ADFS, SAML 2.0, OIDC — but ours is **Directory-Based →
AD/LDAP**.

![Choose identity provider list with the AD/LDAP tile highlighted](https://humbledgeeks.com/wp-content/uploads/2026/06/12-choose-idp-adldap-tile-scaled.jpg)

*Pick AD/LDAP under Directory-Based Identity Provider — not Open LDAP.*

With AD/LDAP selected, click **NEXT**.

![AD/LDAP selected with the Next button active](https://humbledgeeks.com/wp-content/uploads/2026/06/13-choose-idp-next-scaled.jpg)

Then click **CONFIGURE** on task 2 to open the connection form.

![Configure the identity provider task with the Configure button](https://humbledgeeks.com/wp-content/uploads/2026/06/14-configure-idp-button-scaled.jpg)

---

## Step 5 — Directory information (the connection + LDAPS)

This is the heart of it. The **Directory information** form starts blank.

![Blank Directory information form, top](https://humbledgeeks.com/wp-content/uploads/2026/06/15-directory-info-blank-top-scaled.jpg)

![Blank Directory information form, lower fields](https://humbledgeeks.com/wp-content/uploads/2026/06/16-directory-info-blank-mid-scaled.jpg)

*Top: display name and DC discovery. Lower: search attribute, base DN, bind account.*

Fill it in. Leave **DNS Server Location** and **Global Catalog** unchecked, and
specify the DCs explicitly with `ldaps://` so you control exactly which DCs are
used:

- **Directory display name:** `humbledgeeks`
- **Primary domain controller:** `ldaps://dc3-srv-core01.humbledgeeks.com` · Port `636`
- **Certificate for primary DC:** upload `humbledgeeks-ca-chain.pem`
- **Secondary domain controller:** `ldaps://dc3-srv-core02.humbledgeeks.com` · Port `636`

![Directory information with display name and primary/secondary DCs filled](https://humbledgeeks.com/wp-content/uploads/2026/06/17-directory-info-top-filled-scaled.jpg)

*The certificate field appears per-DC the moment you type an `ldaps://` host.*

Continue down the form:

- **Certificate for secondary DC:** upload the **same** `humbledgeeks-ca-chain.pem`
  — both DCs chain to the one root CA
- **Directory search attribute:** `sAMAccountName`
- **Base DN:** `DC=humbledgeeks,DC=com`
- **Bind user name (DN form):** `CN=svc_vcf_sso,OU=Service,OU=HG_Accounts,DC=humbledgeeks,DC=com`
- **Bind user password:** the `svc_vcf_sso` password

![Directory information showing certificates, base DN and the bind DN](https://humbledgeeks.com/wp-content/uploads/2026/06/19-directory-info-certs-binddn-scaled.jpg)

![Directory information with the bind password entered](https://humbledgeeks.com/wp-content/uploads/2026/06/18-directory-info-password-scaled.jpg)

> **Use the DN form for the bind account.** The field's own example is a DN
> (`CN=user1,CN=Users,...`), so enter the full distinguished name, not the UPN.

Click **VALIDATE AND NEXT** — this performs a live bind to AD with these
credentials and validates the certificate chain. If it advances to the review,
everything is correct.

![Directory information review summary](https://humbledgeeks.com/wp-content/uploads/2026/06/20-directory-info-review-scaled.jpg)

*Validation passed — the bind, certs, and both DCs all check out. Click FINISH.*

Back on the sub-flow, task 2 is complete (2/4) and **user/group provisioning**
unlocks.

![Configure Identity Provider showing 2 of 4 tasks complete](https://humbledgeeks.com/wp-content/uploads/2026/06/21-configure-idp-2of4-scaled.jpg)

---

## Step 6 — User and group provisioning

Click **CONFIGURE** on the provisioning task. This is a five-step wizard that
decides *which* AD groups and users flow into VCF.

It opens on **Review Directory Information** — a read-back of what you just
entered.

![Setup Provisioning step 1, Review Directory Information](https://humbledgeeks.com/wp-content/uploads/2026/06/22-provisioning-review-dir-scaled.jpg)

**Attribute Mappings** comes next. For standard AD the defaults are correct
(`userName → sAMAccountName`, `firstName → givenName`, `lastName → sn`,
`email → mail`, `userPrincipalName → userPrincipalName`). Don't change anything.

![Attribute Mappings with standard AD defaults](https://humbledgeeks.com/wp-content/uploads/2026/06/23-provisioning-attr-mappings-scaled.jpg)

*If your schema is standard AD, leave every mapping as-is.*

**Group Provisioning** is where your OU design pays off. It starts blank.

![Group Provisioning, blank](https://humbledgeeks.com/wp-content/uploads/2026/06/24-group-prov-blank-scaled.jpg)

Check **Sync Nested Groups**, enter the **base group DN**
(`OU=VMware,OU=Technologies,OU=HG_Accounts,DC=humbledgeeks,DC=com` — the OU that
holds all my VCF-stack groups), and click **ADD BASE DN**.

![Group Provisioning with the base group DN entered](https://humbledgeeks.com/wp-content/uploads/2026/06/25-group-prov-basedn-scaled.jpg)

The groups under that OU load into a selectable grid. This is also live proof your
bind account can read the directory.

![Group Provisioning with the group list loaded](https://humbledgeeks.com/wp-content/uploads/2026/06/26-group-prov-list-scaled.jpg)

*Every VCF-stack group appears — VCF_Admins, vCenter_*, NSX_*, Aria_*.*

### A real gotcha worth documenting

Here's a mistake I made live, because you'll probably make it too: I clicked
straight through to **User Provisioning** without selecting any groups.

![User Provisioning on the first pass](https://humbledgeeks.com/wp-content/uploads/2026/06/27-user-prov-firstpass-scaled.jpg)

Clicking **NEXT** produced a hard validation error — **"No groups or users were
selected for provisioning."** Provisioning has to sync *something*.

![Validation error: no groups or users selected](https://humbledgeeks.com/wp-content/uploads/2026/06/28-provisioning-error-scaled.jpg)

*The fix: go back to Group Provisioning and actually select groups.*

Back on Group Provisioning, I used **Select All** for this OU. That syncs every
group beneath the base DN (and auto-syncs any added later). It's convenient for a
lab; to be stricter, tick only the specific groups you need. Remember — syncing a
group grants nothing on its own.

![Group Provisioning with Select All enabled](https://humbledgeeks.com/wp-content/uploads/2026/06/29-group-prov-selectall-scaled.jpg)

Now **User Provisioning** — leave the **base user DN blank** so users are pulled
from the synced groups rather than bulk-importing the whole directory.

![User Provisioning with the base user DN left blank](https://humbledgeeks.com/wp-content/uploads/2026/06/30-user-prov-blank-scaled.jpg)

*Blank base user DN = users come from group membership. Exactly what you want.*

The **Review** step summarizes it all: AD/LDAP, the bind DN, ALL groups selected,
0 users (they inherit from groups), and the attribute table. Click **FINISH** —
this starts a background sync that then runs weekly.

![Setup Provisioning review and Finish](https://humbledgeeks.com/wp-content/uploads/2026/06/31-provisioning-review-scaled.jpg)

Provisioning shows complete; click **NEXT** to the optional test login.

![Provisioning complete with Next](https://humbledgeeks.com/wp-content/uploads/2026/06/32-provisioning-complete-next-scaled.jpg)

---

## Step 7 — Test login (prove the whole chain)

This optional step is the single best confidence check before you commit SSO to
your consoles. Click **TEST LOGIN**.

![Test login step ready](https://humbledgeeks.com/wp-content/uploads/2026/06/33-test-login-ready-scaled.jpg)

The broker opens its own login page. In my lab the broker presents a self-signed
certificate, so the browser warns — expected in a lab (in production you'd
CA-sign the broker cert). I continue through.

![Browser certificate warning for the broker](https://humbledgeeks.com/wp-content/uploads/2026/06/34-cert-warning-scaled.jpg)

*Lab reality: the broker's cert isn't browser-trusted yet. Production = CA-sign it.*

On the **Directory Login** page, sign in as a **real AD user in UPN form**
(`allen@humbledgeeks.com`) — not the bind account.

![VMware Directory Login page with an AD user](https://humbledgeeks.com/wp-content/uploads/2026/06/35-directory-login-scaled.jpg)

*UPN format (`user@domain.com`) — bare usernames won't authenticate.*

Success: **"You've logged in with your corporate account!"** That single green
check means broker → LDAPS → both DCs → AD all work end to end.

![Test login success page](https://humbledgeeks.com/wp-content/uploads/2026/06/36-test-login-success-scaled.jpg)

Back in VCF Operations, the inline banner confirms **"Test login is successful"** —
click **DONE**.

![Configure Identity Provider showing the successful test login and Done](https://humbledgeeks.com/wp-content/uploads/2026/06/37-test-login-done-scaled.jpg)

---

## Step 8 — Enable SSO for vCenter and NSX

Back on the main flow (now 50%), click **START** on **Enable SSO for vCenter and
NSX**.

![Configure VCF SSO at 50 percent, step 3 ready](https://humbledgeeks.com/wp-content/uploads/2026/06/38-configure-sso-50pct-scaled.jpg)

The eligible-components list appears. Note the fine print: only **9.0+** components
**not in an ELM ring** are eligible — which is your live confirmation that ELM is
off.

![Enable SSO component list](https://humbledgeeks.com/wp-content/uploads/2026/06/39-enable-sso-list-scaled.jpg)

*My three: dc3-vc01 (Management Domain), dc3-vc02 (workload), dc3-nsx01 (NSX).*

Select **all three** and click **CONFIGURE**.

![All three components selected with Configure](https://humbledgeeks.com/wp-content/uploads/2026/06/40-enable-sso-selected-scaled.jpg)

A **Confirmation required** dialog spells out the impact — enabling SSO
**disables the current authentication source** for vCenter, and you must assign
roles for access. Crucially, *local `@vsphere.local` accounts still work*, so
there's no lockout risk.

![Confirmation dialog, unchecked](https://humbledgeeks.com/wp-content/uploads/2026/06/41-enable-sso-confirm-unchecked-scaled.jpg)

Check the box and click **FINISH**.

![Confirmation dialog checked, Finish active](https://humbledgeeks.com/wp-content/uploads/2026/06/42-enable-sso-confirm-checked-scaled.jpg)

The components move to **In Progress** and configure one by one.

![Enable SSO in progress](https://humbledgeeks.com/wp-content/uploads/2026/06/43-enable-sso-inprogress-scaled.jpg)

When they finish, the flow reaches 75% and **Assign VCF Roles** unlocks.

![Configure VCF SSO at 75 percent](https://humbledgeeks.com/wp-content/uploads/2026/06/44-configure-sso-75pct-scaled.jpg)

---

## Step 9 — Assign VCF roles (so AD admins actually have access)

Optional in the wizard, but skip it and your AD admins authenticate with **zero
access**. Click **START**.

The **Assign VCF Roles** page lists every synced group. Note the JIT-provisioning
note — VCF-level roles are new in 9.1, and groups become assignable after first
login.

![Assign VCF Roles, groups list](https://humbledgeeks.com/wp-content/uploads/2026/06/45-assign-roles-groups-scaled.jpg)

Select **`VCF_Admins`** and click **ASSIGN**.

![VCF_Admins selected with Assign](https://humbledgeeks.com/wp-content/uploads/2026/06/46-assign-vcf-admins-checked-scaled.jpg)

> **Scope it deliberately.** I initially had three "admin" groups selected here.

![Assign page with three groups selected](https://humbledgeeks.com/wp-content/uploads/2026/06/47-assign-three-groups-scaled.jpg)

> But VCF-level roles should go to the **fleet-admin group only** — `vCenter_Admins`
> and `NSX_Admins` get their roles at the *component* level (inside vCenter/NSX), so
> I removed them and kept just `VCF_Admins`.

![Assign page with only VCF_Admins](https://humbledgeeks.com/wp-content/uploads/2026/06/48-assign-vcf-admins-only-scaled.jpg)

Set the **Scope** first — choosing **"Components with dc3-vidb.humbledgeeks.com"**
(fleet-wide) is what unlocks the VCF-level roles.

![Scope dropdown options](https://humbledgeeks.com/wp-content/uploads/2026/06/49-scope-dropdown-scaled.jpg)

Then pick the **Role**. With the fleet scope set, **VCF Administrator** becomes
selectable (the VCF roles are greyed until a scope is chosen).

![Role dropdown options](https://humbledgeeks.com/wp-content/uploads/2026/06/50-role-dropdown-scaled.jpg)

*Scope = Components with dc3-vidb (fleet-wide); Role = VCF Administrator.*

Confirm Scope + Role + Valid Until (Never Expires) and click **ASSIGN**.

![Scope and Role selected, ready to assign](https://humbledgeeks.com/wp-content/uploads/2026/06/51-scope-role-selected-scaled.jpg)

Green banner — **"Changes successful."** `VCF_Admins` now holds VCF Administrator
(effective at next login).

![Roles assigned successfully](https://humbledgeeks.com/wp-content/uploads/2026/06/52-roles-assigned-success-scaled.jpg)

> **VCF-level vs component roles.** This screen grants *fleet* access. Per-console
> admin for **vCenter** and **NSX** is assigned inside those consoles; the
> privileges combine. My plan: `VCF_Admins` → VCF Administrator (fleet);
> `vCenter_Full_Admins` → vCenter Administrator; `NSX_Admins` → NSX Enterprise
> Admin; `Aria_Admins` → VCF Operations Administrator; read-only groups to their
> Read-only equivalents. `vCenter_Admins` is left unmapped (redundant), and the
> `*_Service_Accounts` groups get no interactive roles.

---

## Step 10 — Finish setup (and back it up)

Click **FINISH SETUP** — the wizard is 100%.

![Configure VCF SSO at 100 percent](https://humbledgeeks.com/wp-content/uploads/2026/06/53-configure-sso-100pct-scaled.jpg)

The confirmation dialog **strongly recommends backing up** the SSO/identity
configuration. Click **EXPORT CONFIGURATION** and keep that file — it's your
restore point before any future "Reset SSO." Then **CONTINUE**.

![Finish Setup dialog with Export Configuration](https://humbledgeeks.com/wp-content/uploads/2026/06/54-finish-setup-modal-scaled.jpg)

*Export the config now, while it's clean. Future-you will thank present-you.*

---

## Step 11 — Join the management appliances (clear the red)

On the **VCF SSO Overview**, the VCF *Instance* is fully configured (**3/3**)...

![Overview showing VCF Instances 3 of 3 configured](https://humbledgeeks.com/wp-content/uploads/2026/06/55-overview-instances-3of3-scaled.jpg)

...but **VCF Management Status** is **red — 2 Not Configured**. Those are the
**VCF Operations** and **VCF Automation** appliances. Joining them lets you sign
into *those* consoles with AD too (right now you're in VCF Operations as a local
admin).

![Overview with VCF Management red, 2 not configured](https://humbledgeeks.com/wp-content/uploads/2026/06/56-overview-management-red-scaled.jpg)

On the **VCF Management** tab, tick **both** appliances and click **JOIN VCF SSO**.

![VCF Management tab with both appliances selected and Join VCF SSO](https://humbledgeeks.com/wp-content/uploads/2026/06/57-management-join-selected-scaled.jpg)

On **Choose SSO**, the JOIN button is greyed until you pick a broker...

![Join VCF SSO with broker not yet selected](https://humbledgeeks.com/wp-content/uploads/2026/06/58-join-broker-unselected-scaled.jpg)

...select **`dc3-vidb.humbledgeeks.com`** and click **JOIN**.

![Join VCF SSO with the dc3-vidb broker selected](https://humbledgeeks.com/wp-content/uploads/2026/06/59-join-broker-selected-scaled.jpg)

Acknowledge the role-assignment confirmation and click **FINISH**.

![Join VCF SSO confirmation dialog](https://humbledgeeks.com/wp-content/uploads/2026/06/60-join-confirm-scaled.jpg)

Both appliances flip to **Configured**, and **VCF Management Status** turns
**blue — 2 Configured**. No more red.

![VCF SSO Overview fully configured, no red](https://humbledgeeks.com/wp-content/uploads/2026/06/61-overview-all-configured-scaled.jpg)

*The finish line: VCF Instance 3/3, VCF Management 2/2, broker 0 issues. The whole environment now authenticates against Humbledgeeks AD.*

---

## Verify

- **VCF SSO Overview:** Identity Broker `dc3-vidb` = **0 Issues**; VCF Instance and
  VCF Management both blue.
- **AD login:** log out and back in to VCF Operations as a `VCF_Admins` member in
  UPN form (`user@humbledgeeks.com`); confirm the VCF Administrator role applies.
- **Component access:** after assigning component-level roles, confirm AD admins
  can log into vCenter and NSX.

## What's left (optional, not blocking)

- **Component-level roles** in vCenter (`vCenter_Full_Admins` → Administrator) and
  NSX (`NSX_Admins` → Enterprise Admin), plus the read-only groups.
- **CA-sign the broker certificate** so the login page stops throwing the browser
  warning (lab convenience now; production hygiene later).

---

## Gotchas worth remembering

- **SDDC Manager UI** accepts only local `@vsphere.local` logins (its APIs accept
  SSO users). ESX is excluded too.
- **vCenter's prior identity config is overridden** by VCF SSO — re-assign roles
  afterward.
- **Users/groups are never migrated** from a pre-existing vCenter identity source.
- **Login format is UPN** (`user@domain.com`), not a bare username.
- **Provisioning needs a selection** — "ADD BASE DN" loads the groups, but you must
  actually *select* them, or you'll hit the "nothing selected" error.
- **Bind account uses the DN form**, not the UPN.
- **Back up** VCF Operations and the broker after SSO changes (Export
  Configuration).
- **Manage identity only from VCF Operations** from now on.

---

## What's next

With identity sorted, the series moves into making the platform do real work — in
order, because each step builds on the one before it:

1. **NetApp ONTAP tools / VASA (vVols)** — deploy the ONTAP tools appliance in the
   management domain and present a vVols datastore for policy-based VM storage on
   the FlexPod.
2. **Kubernetes on the workload domain (VKS)** — stand up a vSphere Kubernetes
   Service cluster and run a container (yes, the obligatory Doom pod) as the
   modern-apps use case.
3. **Cross-vCenter migration** — bring a VM from a legacy vSphere 8.0U3 environment
   into the VCF 9.1 workload domain via Advanced Cross vCenter vMotion.
4. **Backup and recovery** — VCF-native backup/restore plus the NetApp SnapCenter
   plug-in.
5. **Lifecycle management** — register the software depot and apply an update
   through VCF Operations.

And to finish closing out this identity thread: the **component-level vCenter and
NSX role assignments** (`vCenter_Full_Admins` → Administrator, `NSX_Admins` →
Enterprise Admin) and **CA-signing the broker certificate** so the login page stops
throwing the browser warning.

*Next post in the series: [link to your next topic].*


