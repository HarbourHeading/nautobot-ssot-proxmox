from nautobot.apps import NautobotAppConfig

class NautobotSSoTProxmoxConfig(NautobotAppConfig):
    """
    AppConfig required by Nautobot.
    No DB models are introduced in this minimal app.
    """
    name = "nautobot_ssot_proxmox"
    verbose_name = "Nautobot SSoT: Proxmox"
    version = "0.1.0"
    author = "FadenB"
    author_email = "fadenb@utzutzutz.net"
    description = "Import Proxmox inventory (VMs/LXCs) into Nautobot via SSoT."
