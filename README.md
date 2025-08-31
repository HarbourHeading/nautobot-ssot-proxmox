# Nautobot SSoT: Proxmox (minimal)

Import Proxmox VE inventory (QEMU VMs and LXC containers) into Nautobot as VirtualMachines inside a single Cluster, using the Nautobot SSoT framework (DiffSync + Jobs). You get a built-in diff preview (dry-run) and standard Job scheduling.

This is intentionally minimal and safe-by-default:
- Creates (or updates) one Cluster by name
- Upserts VirtualMachines keyed by immutable proxmox_vmid custom field
- Sets VM attributes: name, vCPUs, memory (MB), status (Active or Offline), cluster, and custom fields (node, type)
- Does not delete by default; enable deletions via config

## Prerequisites

- Nautobot 2.x up and running
- Nautobot SSoT app installed and enabled
- A Proxmox 8.x API token with read-only privileges (PVEAuditor is fine)
- Ubuntu 24.04 host for Nautobot services (assumed)

## Install

1) Activate your Nautobot virtual environment (e.g., `source /opt/nautobot/venv/bin/activate` or `source .venv/bin/activate`).

2) Install this plugin using `pip`. This will install the package in "editable" mode and automatically handle all dependencies defined in `pyproject.toml`.
    # From within the root of this cloned repository:
    pip install -e .

3) Enable apps in nautobot_config.py:

    PLUGINS = [
        "nautobot_ssot",
        "nautobot_ssot_proxmox",
    ]

    PLUGINS_CONFIG = {
        "nautobot_ssot_proxmox": {
            "PROXMOX_URL": "https://pve.example:8006",
            "PROXMOX_USER": "nb-sync@pve",
            "PROXMOX_TOKEN_NAME": "nautobot",
            "PROXMOX_TOKEN_VALUE": "REDACTED_TOKEN_VALUE",
            "VERIFY_SSL": True,

            "CLUSTER_NAME": "Prod Proxmox",
            "CLUSTER_TYPE_NAME": "Proxmox VE",

            "DELETE_MISSING": False,
        },
    }

4) Apply migrations and restart services:
    nautobot-server migrate
    nautobot-server collectstatic --no-input
    sudo systemctl restart nautobot nautobot-worker

## Proxmox setup

Create a dedicated API user and token in Proxmox (UI: Datacenter -> Permissions -> API Tokens). Grant the user PVEAuditor at the root path "/". Use the generated token name and secret in PLUGINS_CONFIG.

## How it works

- Job name: "Proxmox: Import inventory" under Apps -> SSoT.
- Dry-run by default. You will see the diff before applying.
- Identifiers:
  - VM: custom_fields.proxmox_vmid (immutable)
  - Cluster: name
- Synced attributes:
  - VM: name, vcpus, memory (MB), status__name ("Active" if running, else "Offline"), cluster__name, CFs proxmox_node, proxmox_type.

## Run a sync

1) UI: Apps -> SSoT -> Data Sources -> "Proxmox: Import inventory".
2) Run with dry-run first.
3) If the diff looks good, uncheck dry-run (commit) and run again.

## Scheduling

Create a Scheduled Job in the Nautobot UI to run every 5 to 15 minutes, as desired.

## Extending later

- Add VMInterfaces and IPs: introduce a VMInterfaceModel and enumerate NICs via per-VM endpoints, then map to Nautobot Virtualization interfaces and IPAM.
- Multiple clusters: emit multiple ClusterModel objects and set cluster__name per VM.
- Deletion policy: keep DELETE_MISSING=False for safety; or enable and let SSoT delete.

## Troubleshooting

- Missing config keys: check PLUGINS_CONFIG in nautobot_config.py.
- SSL errors: set VERIFY_SSL=False to test, then fix CA trust.
- Status mapping: "running" -> "Active", everything else -> "Offline".
- Permissions: use a read-only Proxmox token; this job uses GET endpoints only.

## Uninstall

1) Remove "nautobot_ssot_proxmox" from PLUGINS.
2) pip uninstall nautobot-ssot-proxmox and restart Nautobot services.
