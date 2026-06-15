# ESXi Hardening & NTP — Getting Your B200s Ready for VCF 9.0

<!-- IMAGE PLACEHOLDER -->

## Picking Up Where We Left Off

If you've been following along with the Zero to VCAP series, we just wrapped up
configuring eight Cisco UCS B200 blades with direct-attached Fibre Channel storage
from the NetApp ASA A30 — a full FlexPod CVD build. The blades are racked, zoned,
booted, and ESXi is up across all eight hosts. That part felt good.

Before I hand these hosts off to the VCF 9.0 installer, though, there's one more
step I always do on every install — and I mean every install. I run a security
hardening script against the ESXi hosts.

This isn't optional for me. Whether it's a customer engagement, a lab build, or
an exam prep environment, I want all my ESXi hosts configured the same way before
anything else touches them. Consistent DNS, consistent NTP, consistent security
settings. It doesn't matter how many hosts you have — if one is drifting, you'll
find out at the worst possible moment, usually mid-VCF deployment when SDDC Manager
is validating preflight checks.

This post walks through the script I use, what it does, and how I run it. I'll share
screenshots of me running it live against the B200s. If you want a copy, it's on my
GitHub — link at the bottom.

---

## The Script: `ESXi_Hardening_V6h.ps1`

This is the current version of a hardening script I've been evolving over several
years of FlexPod and VCF deployments. It's co-authored with Gary Matsuda and lives
in the `infra-automation` repo. The "V6h" in the name means version 6, hardening-only
— I stripped rollback out of earlier versions because this is deliberate one-way
configuration, not something you should need to undo.

The core philosophy behind the script:

- **Dry run first, always.** You see exactly what would change before anything is
  applied. I've built this as a hard guardrail — the script prompts you to run
  dry mode by default.
- **Verify after every change.** The script reads back each setting after it applies
  it to confirm the value stuck. If the primary set method doesn't work, it falls
  back to the raw vSphere API (`AdvancedOptionManager.UpdateOptions`) and verifies again.
- **HTML report on every run.** After dry run and after apply, you get a themed
  dashboard with KPI cards showing how many settings were changed, how many were
  already compliant, and a full per-host results table.
- **Flexible targeting.** You can point it at a vCenter cluster, a list of standalone
  hosts, or a CSV file. In the B200 scenario I'm connecting via vCenter since all
  eight hosts are already discovered.

<!-- IMAGE PLACEHOLDER — script launch / safety prompt in VS Code terminal -->

---

## What the Script Configures

The script applies nine advanced settings, alphabetically sorted. Here's what each
one does and why I include it in the pre-VCF checklist.

### `Config.HostAgent.log.level` → `info`

Sets the host agent log verbosity to `info`. This is the standard production value —
detailed enough to be useful for troubleshooting during VCF bring-up, without
flooding the logs. I've seen hosts with this set to `verbose` generate log files
large enough to cause disk pressure on the VMFS scratch partition during a deployment.
Keep it at `info`.

### `Config.HostAgent.plugins.solo.enableMob` → `false`

Disables the Managed Object Browser (MOB). The MOB is a web-based debug interface
that exposes the full vSphere object model to anyone who can authenticate to the
host. It's off by default in recent ESXi builds, but I've seen it get enabled in
lab environments where someone needed it for one-off debugging and never turned it
back off. VCF audits this. Make sure it's off before you run the installer.

### `Mem.ShareForceSalting` → `2`

Memory page salting. Setting this to `2` means ESXi always salts memory pages before
sharing them between VMs, which prevents cross-VM side-channel attacks based on
memory deduplication. In a management domain where control plane VMs are running
alongside tenant workloads, this matters. The three values are `0` (no salting),
`1` (salt when VMs belong to different users), and `2` (always salt). Use `2`.

### `Security.AccountLockFailures` → `5`

Lockout threshold for local accounts. After five consecutive failed login attempts,
the account locks. Without this, there's no throttle on brute-force attempts against
root or any other local account. This is a CIS VMware ESXi Benchmark requirement and
a VCF security audit item.

### `Security.AccountUnlockTime` → `900`

How long a locked account stays locked — 900 seconds, which is 15 minutes. Long
enough to be meaningful as a deterrent, short enough that a legitimate admin doesn't
need to call someone for an unlock after a bad night. If you set this to `0`, the
account locks permanently until manually unlocked.

### `Security.PasswordHistory` → `5`

Prevents reuse of the last five passwords. Required by most compliance frameworks
and expected in any VCF environment where credential rotation is happening.

### `Security.PasswordQualityControl` → `similar=deny retry=3 min=disabled,disabled,disabled,disabled,15`

The password complexity policy. This one looks intimidating but the short version is:
passwords must be at least 15 characters, cannot be too similar to the current
password, and you get three attempts before it rejects the input. This aligns with
NIST SP 800-63B and with Broadcom's VCF security hardening documentation. The four
`disabled` values in the `min` parameter disable individual character class minimums
(lowercase, uppercase, digits, symbols) — the policy relies on minimum length instead,
which is the current guidance.

### `UserVars.HostClientCEIPOptIn` → `2`

Disables CEIP telemetry opt-in on the host client. Value `2` is opted out. In most
enterprise and lab environments you don't want outbound telemetry from hosts
regardless of whether you're air-gapped. VCF manages CEIP configuration from SDDC
Manager anyway, so set a clean baseline here.

### `UserVars.SuppressShellWarning` → `1`

Suppresses the persistent vSphere Client warning that appears when ESXi Shell or SSH
is enabled on a host. During pre-deployment automation I have SSH enabled — it's
needed to run scripts and validate configuration. This setting keeps the UI from
surfacing that warning as a noisy banner on every host. Once VCF is deployed and I
don't need shell access anymore, I'll disable SSH.

---

## Running the Script Against the B200s

I'm running this from VS Code in the `infra-automation` repo. Open the integrated
terminal and navigate to the Hardening folder:

```powershell
cd .\VMware\ESXi\PowerShell\Hardening\
.\ESXi_Hardening_V6h.ps1
```

### Step 1 — Dry Run First

The first prompt is the safety notice: `Run in DRY MODE first? (y/n)`. The answer
is always `y` the first time. Dry run simulates every change, shows you what the
current value is and what it would be changed to, and produces a full HTML report.
Nothing on the hosts is touched.

<!-- IMAGE PLACEHOLDER — dry run mode prompt and console output -->

### Step 2 — Connect via vCenter

For the B200 build I'm selecting option `1` (vCenter cluster). I enter the vCenter
FQDN and the cluster name for the eight B200 hosts. The script connects, discovers
all hosts in that cluster, and confirms the count before proceeding.

<!-- IMAGE PLACEHOLDER — connection selection and host discovery output -->

### Step 3 — Accept Recommended Values

When it asks "Apply all Recommended Values?", I answer `y`. The defaults in the
script are the correct settings — I maintain these values based on the VMware
Security Configuration Guide and CIS Benchmark for ESXi. If you want to review
each setting individually before applying, answer `n` and it walks you through
them one by one with the recommended value shown.

### Step 4 — Review the HTML Report

After dry run completes, the script offers to open the HTML report in your browser.
Open it. The report shows a KPI card row at the top (hosts processed, settings that
would change, settings already compliant, errors) and a full per-host table at the
bottom showing every setting, the current value, and what it would be changed to.

<!-- IMAGE PLACEHOLDER — HTML report KPI dashboard -->

<!-- IMAGE PLACEHOLDER — per-host results table in HTML report -->

Review this before you apply. If you see anything unexpected — a setting that's
already at the wrong value, a host that errored during connection — address it
before moving on.

### Step 5 — Apply Mode

Once dry run looks clean, the script asks: `Dry run finished. Switch to APPLY mode
and rerun now with the same settings and hosts?`. Answer `y`. It runs the same pass
in live mode: applies each setting, verifies the read-back matches the intended
value, and logs everything. A second HTML report is generated for the apply run.

<!-- IMAGE PLACEHOLDER — apply mode console output with verified checkmarks -->

<!-- IMAGE PLACEHOLDER — apply run HTML report -->

---

## NTP: Do This Before the Script, or Right After

The hardening script does not configure NTP — that's intentional, since NTP is
infrastructure configuration rather than a security hardening setting. But I'm
treating it as part of the same pre-VCF prep step because VCF 9.0 is extremely
sensitive to time skew. If your hosts aren't synced before the installer runs, you
will hit certificate validation failures and vSAN configuration errors.

Run this to check the current NTP state across all hosts in your cluster:

```powershell
Get-VMHost | Select-Object Name,
    @{N="NTP Servers"; E={ (Get-VMHostNtpServer $_) -join ", " }},
    @{N="NTP Running"; E={ (Get-VMHostService $_ | Where-Object { $_.Key -eq "ntpd" }).Running }},
    @{N="NTP Policy";  E={ (Get-VMHostService $_ | Where-Object { $_.Key -eq "ntpd" }).Policy  }} |
    Format-Table -AutoSize
```

You want every host showing the same NTP server, `True` for running, and `on` for
policy. If anything is inconsistent, remediate with this block:

```powershell
$ntpServer = "time.nist.gov"   # replace with your internal NTP source if applicable

Get-VMHost | ForEach-Object {
    $h = $_
    Write-Host "Configuring NTP on $($h.Name)..." -ForegroundColor Cyan

    # Clean slate — remove any existing NTP entries
    $existing = Get-VMHostNtpServer -VMHost $h
    if ($existing) {
        Remove-VMHostNtpServer -VMHost $h -NtpServer $existing -Confirm:$false
    }

    # Set your NTP server
    Add-VMHostNtpServer -VMHost $h -NtpServer $ntpServer | Out-Null

    # Open the NTP firewall rule
    $ntpRule = Get-VMHostFirewallException -VMHost $h |
        Where-Object { $_.Name -eq "NTP client" }
    if ($ntpRule -and -not $ntpRule.Enabled) {
        Set-VMHostFirewallException -Exception $ntpRule -Enabled $true | Out-Null
    }

    # Set ntpd to start automatically and restart the service
    Get-VMHostService -VMHost $h | Where-Object { $_.Key -eq "ntpd" } |
        Set-VMHostService -Policy "on" | Out-Null
    Get-VMHostService -VMHost $h | Where-Object { $_.Key -eq "ntpd" } |
        Restart-VMHostService -Confirm:$false | Out-Null

    Write-Host "  ✅ NTP configured on $($h.Name)" -ForegroundColor Green
}
```

Run the verification query again after remediation and confirm every host returns
the same output before moving on.

> **If you're in a corporate network or air-gapped lab:** replace `time.nist.gov`
> with your internal NTP source. Active Directory domain controllers running W32tm
> work well as NTP sources for ESXi hosts in an enterprise environment.

---

## Pre-VCF 9.0 Checklist: Where Things Should Stand

After hardening and NTP, here's the state I want to verify across all eight B200s
before the VCF 9.0 installer gets anywhere near them:

| Item | Expected State | How to Check |
|------|---------------|--------------|
| ESXi build | VCF 9.0 compatible | `Get-VMHost \| Select Name, Version, Build` |
| NTP server | Same on all hosts, ntpd running, policy = on | PowerCLI NTP query above |
| MOB disabled | `enableMob = false` | Hardening script HTML report |
| Password policy | 15-char min, deny similar, history=5 | Hardening script HTML report |
| Account lockout | Failures=5, UnlockTime=900 | Hardening script HTML report |
| Memory salting | `Mem.ShareForceSalting = 2` | Hardening script HTML report |
| CEIP opted out | `HostClientCEIPOptIn = 2` | Hardening script HTML report |
| Log level | `Config.HostAgent.log.level = info` | Hardening script HTML report |
| DNS resolution | FQDN resolves forward and reverse | `Resolve-DnsName <esxi-fqdn>` |
| VMkernel adapters | Management, vMotion, NSX TEP configured | `Get-VMHostNetworkAdapter` |
| No active alarms | All hosts green in vCenter | vSphere Client → Hosts and Clusters |

When that table is all green, the hosts are ready. Next post covers the VCF 9.0
Cloud Builder configuration and the bringup JSON — the part where it all comes
together.

---

## Get the Script

The hardening script is in the HumbledGeeks `infra-automation` repo:

```
infra-automation/VMware/ESXi/PowerShell/Hardening/ESXi_Hardening_V6h.ps1
```

Feel free to grab it, adapt the settings to your environment, and run it before
any VCF deployment. If you make improvements, pull requests are welcome.

[github.com/humbledgeeks/infra-automation](https://github.com/humbledgeeks/infra-automation)

---

Follow along at [HumbledGeeks.com](https://humbledgeeks.com) or connect with me
on LinkedIn. We're almost at the VCF installer — see you in the next one.
