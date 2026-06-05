# Nautobot SSoT Proxmox

Unofficial Nautobot SSoT sync script to fetch basic VM information from Proxmox VE (remote) into Nautobot (local).

![nautobot-vm-example.png](images/nautobot-vm-example.png)

Observed working for:
- Nautobot 3.1.3
- Proxmox VE 9.2.3

## Install

### Proxmox API token

Assuming you're using Proxmox VE, in your Proxmox instance, configure a `User` 
(Datacenter > Permissions > Users) and an `API token` (Datacenter > Permissions > API Tokens).
Configure scope/permissions (Datacenter > Permissions) for the user or API with Path: `/` and Role `PVEAuditor`.
Permissions can likely be scoped even smaller by adjusting path and creating a new role.

### Nautobot plugin

Currently, the plugin is not uploaded to any other platforms than GitHub. The recommended steps are to install it locally.

Clone the repository
````bash
git clone https://github.com/HarbourHeading/nautobot-ssot-proxmox.git
````

Update `local_requirements.txt` or equivalent dependency configuration (e.g. `pyproject.toml`) to include
````
nautobot-ssot-proxmox @ file:///srv/nautobot/nautobot-ssot-proxmox
````

Enable and configure the plugin in `nautobot_config.py`:
````python
PLUGINS = ["nautobot_ssot", "nautobot_ssot_proxmox"]

PLUGINS_CONFIG = {
    "nautobot_ssot_proxmox": {
        "proxmox_url": "https://pve.example.com",
        "proxmox_port": "443",  # defaults to 8006 if not set
        "proxmox_user": "nautobot-sync@pam",
        "proxmox_token_name": "nautobot-sync-token",
        "proxmox_token_value": "jc73dsef-3gr4-3gry-cgd4-a257hnjlfdwa",
        "verify_ssl": True,
        "cluster_name": "homelab",
        "cluster_type_name": "Proxmox VE",
        "certificate": "/srv/nautobot/client_certificate.p12", # optional
        "certificate_passphrase": "my-password",  # optional
        "http_proxy": "http://proxy.example:3128", # optional
        "https_proxy": "http://proxy.example:3128", # optional
    },
}
````

Reload nautobot
````
nautobot-server post_upgrade
````

Then restart nautobot
````
systemctl restart nautobot nautobot-worker nautobot-scheduler
````

## Run

Just run the nautobot job `Proxmox -> Nautobot`

## Roadmap

- [ ] Fetch VM disks to get total disk space.
- [ ] Fetch VM network devices to get and create IP Addresses, ip ranges and interfaces.
- [ ] Make what is currently the plugin config, into job fields to allow syncing multiple different proxmox instances.