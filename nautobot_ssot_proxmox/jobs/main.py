"""Proxmox to nautobot sync job."""

from typing import Any
from django.contrib.contenttypes.models import ContentType
from django.templatetags.static import static
from django.urls import reverse
from diffsync.enum import DiffSyncFlags
from nautobot.extras.models import CustomField
from nautobot.virtualization.models import ClusterType, VirtualMachine
from nautobot_ssot.jobs.base import DataMapping, DataSource

from ..config import ProxmoxConfig
from ..diffsync.adapter_proxmox import ProxmoxAdapter
from ..diffsync.adapter_nautobot import NautobotInventoryAdapter

name = "SSoT Proxmox"


def _get_config() -> ProxmoxConfig:
    """Helper to load config into dataclass."""

    from django.conf import settings
    plugin_settings = settings.PLUGINS_CONFIG.get("nautobot_ssot_proxmox", {})

    # Filter only fields present in ProxmoxConfig
    valid_keys = ProxmoxConfig.__annotations__.keys()
    filtered = {k: v for k, v in plugin_settings.items() if k in valid_keys}
    return ProxmoxConfig(**filtered)


def _ensure_cluster_type(type_name: str) -> None:
    """Make sure the ClusterType referenced by the job exists."""

    ClusterType.objects.get_or_create(name=type_name)


def _ensure_vm_custom_fields() -> None:
    """Create required CustomFields on VirtualMachine if they do not exist."""

    vm_ct = ContentType.objects.get_for_model(VirtualMachine)

    wanted = [
        ("proxmox_vmid", "Proxmox VMID"),
        ("proxmox_node", "Proxmox Node"),
        ("proxmox_type", "Proxmox Type"),
        ("hostname", "Hostname"),
    ]

    for key, label in wanted:
        cf, _ = CustomField.objects.get_or_create(
            key=key,
            defaults={"label": label, "type": "text"},
        )
        if vm_ct not in cf.content_types.all():
            cf.content_types.add(vm_ct)

class ProxmoxDataSource(DataSource):  # pylint: disable=too-many-instance-attributes
    """Sync Virtual Machines from Proxmox into Nautobot."""

    def __init__(self):
        super().__init__()
        self.diffsync_flags = (
            self.diffsync_flags | DiffSyncFlags.SKIP_UNMATCHED_DST  # pylint: disable=unsupported-binary-operation
        )

    class Meta:
        """Metaclass attributes of ProxmoxDataSource."""

        name = "Proxmox -> Nautobot"
        description = "Import Proxmox VMs/LXCs into Nautobot Cluster as VirtualMachines (SSoT)."
        data_source = "Proxmox (remote)"
        data_source_icon = static("img/nautobot_logo.png")
        commit_default = True

    @classmethod
    def data_mappings(cls):
        """This Job maps objects from Proxmox to Nautobot."""

        return (
            DataMapping("Proxmox Cluster", None, "Nautobot Cluster", reverse("virtualization:cluster_list")),
            DataMapping("Proxmox VM/LXC", None, "Nautobot VirtualMachine", reverse("virtualization:virtualmachine_list")),
            DataMapping("Proxmox VM Network", None, "Nautobot Prefix", reverse("ipam:prefix_list")),
            DataMapping("Proxmox VM IP", None, "Nautobot IPAddress", reverse("ipam:ipaddress_list")),
            DataMapping("Proxmox VM Interface", None, "Nautobot VM Interface", reverse("virtualization:vminterface_list")),
            DataMapping("Proxmox VM Tags", None, "Nautobot VM Tags", reverse("virtualization:tags_list")),
        )

    def config_information(self) -> dict[str, Any]:
        """Display useful configuration details in the Job form."""

        cfg = _get_config()
        return {
            "Proxmox URL": cfg.proxmox_url,
            "Proxmox Port": cfg.proxmox_port or "8006",
            "Cluster name": cfg.cluster_name,
            "Cluster type": cfg.cluster_type_name,
            "Verify SSL": cfg.verify_ssl,
            "Client Cert": "Configured" if cfg.certificate else "None",
            "Cert Password": "********" if cfg.certificate_passphrase else "None",
            "HTTP Proxy": cfg.http_proxy or "None",
            "HTTPS Proxy": cfg.https_proxy or "None",
        }

    def load_source_adapter(self):
        """Build and load the Proxmox (source) adapter."""

        cfg = _get_config()
        self.source_adapter = ProxmoxAdapter(config=cfg, job=self)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Prepare Nautobot (target) and load the adapter."""

        cfg = _get_config()
        _ensure_cluster_type(cfg.cluster_type_name)
        _ensure_vm_custom_fields()

        self.target_adapter = NautobotInventoryAdapter(job=self)
        self.target_adapter.load()

    def execute_sync(self, *args, **kwargs) -> None:
        """Override to ensure deletions are never allowed."""

        return super().execute_sync(*args, **kwargs)
