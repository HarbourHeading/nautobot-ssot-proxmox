"""
SSoT Job class that orchestrates the sync.

- Inherits from nautobot_ssot.jobs.DataSource to get the standard diff/sync UI
- Leverages contrib adapters/models for Nautobot CRUD
- Ensures required ClusterType and Custom Fields exist before loading Nautobot
"""
from typing import Dict, Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from nautobot.extras.jobs import Job
from nautobot_ssot.jobs import DataSource

from nautobot.extras.models import CustomField
from nautobot.virtualization.models import ClusterType, VirtualMachine

from .const import (
    CFG_PROXMOX_URL,
    CFG_PROXMOX_USER,
    CFG_PROXMOX_TOKEN_NAME,
    CFG_PROXMOX_TOKEN_VALUE,
    CFG_VERIFY_SSL,
    CFG_CLUSTER_NAME,
    CFG_CLUSTER_TYPE_NAME,
    CFG_DELETE_MISSING,
    CF_PROXMOX_VMID,
    CF_PROXMOX_NODE,
    CF_PROXMOX_TYPE,
)
from .diffsync.adapter_proxmox import ProxmoxAdapter
from .diffsync.adapter_nautobot import NautobotInventoryAdapter


def _plugin_config() -> Dict[str, Any]:
    """Read our config block from Nautobot settings."""
    return settings.PLUGINS_CONFIG.get("nautobot_ssot_proxmox", {})


def _ensure_cluster_type(type_name: str) -> None:
    """Make sure the ClusterType referenced by the job exists."""
    ClusterType.objects.get_or_create(name=type_name)


def _ensure_vm_custom_fields() -> None:
    """
    Create required CustomFields on VirtualMachine if they do not exist.

    Nautobot 2.x uses 'key' and 'label' on CustomField. We add them to the
    VirtualMachine content type so we can write CF data via the ORM.
    """
    vm_ct = ContentType.objects.get_for_model(VirtualMachine)

    wanted = [
        (CF_PROXMOX_VMID, "Proxmox VMID"),
        (CF_PROXMOX_NODE, "Proxmox Node"),
        (CF_PROXMOX_TYPE, "Proxmox Type"),
    ]
    for key, label in wanted:
        cf, _ = CustomField.objects.get_or_create(
            key=key,
            defaults={"label": label, "type": "text"},
        )
        # Ensure the field is attached to VirtualMachine
        if vm_ct not in cf.content_types.all():
            cf.content_types.add(vm_ct)


class ProxmoxToNautobot(DataSource, Job):
    """
    Proxmox -> Nautobot SSoT Data Source.

    You will find it in Nautobot under:
    Apps -> SSoT -> Data Sources -> "Proxmox: Import inventory"
    """
    class Meta:
        name = "Proxmox: Import inventory"
        description = "Import Proxmox VMs/LXCs into Nautobot Cluster as VirtualMachines (SSoT)."
        commit_default = False  # default to dry-run

    def config_information(self) -> Dict[str, Any]:
        """
        Display useful configuration details in the Job form.
        """
        cfg = _plugin_config()
        return {
            "Proxmox URL": cfg.get(CFG_PROXMOX_URL, "<unset>"),
            "Cluster name": cfg.get(CFG_CLUSTER_NAME, "<unset>"),
            "Cluster type": cfg.get(CFG_CLUSTER_TYPE_NAME, "Proxmox VE"),
            "Verify SSL": bool(cfg.get(CFG_VERIFY_SSL, True)),
            "Delete missing": bool(cfg.get(CFG_DELETE_MISSING, False)),
        }

    def load_source_adapter(self):
        """
        Build and load the Proxmox (source) adapter.
        """
        cfg = _plugin_config()
        required = [
            CFG_PROXMOX_URL, CFG_PROXMOX_USER,
            CFG_PROXMOX_TOKEN_NAME, CFG_PROXMOX_TOKEN_VALUE,
            CFG_CLUSTER_NAME,
        ]
        missing = [k for k in required if not cfg.get(k)]
        if missing:
            raise RuntimeError(f"Missing required plugin config keys: {', '.join(missing)}")

        self.source_adapter = ProxmoxAdapter(config=cfg, job=self)
        self.source_adapter.load()

    def load_target_adapter(self):
        """
        Prepare Nautobot (target) by ensuring:
        - ClusterType exists
        - CustomFields exist on VirtualMachine
        Then load the Nautobot adapter.
        """
        cfg = _plugin_config()
        _ensure_cluster_type(cfg.get(CFG_CLUSTER_TYPE_NAME, "Proxmox VE"))
        _ensure_vm_custom_fields()

        self.target_adapter = NautobotInventoryAdapter(job=self)
        self.target_adapter.load()

    def data_mapping(self) -> Dict[str, Any]:
        """
        Optional: expose a short mapping summary in the UI.
        """
        return {
            "Cluster.name": "Config[CLUSTER_NAME]",
            "Cluster.type__name": "Config[CLUSTER_TYPE_NAME]",
            "VirtualMachine.identifiers": "custom_fields.proxmox_vmid",
            "VirtualMachine.attributes": [
                "name", "vcpus", "memory (MB)", "status__name", "cluster__name",
                "custom_fields.proxmox_node", "custom_fields.proxmox_type",
            ],
        }

    def execute_sync(self, *, dry_run: bool = True) -> None:
        """
        Override to enforce delete policy based on config.
        Otherwise defer to the base class implementation.
        """
        delete = bool(_plugin_config().get(CFG_DELETE_MISSING, False))
        return super().execute_sync(dry_run=dry_run, allow_delete=delete)


# Register jobs with Nautobot job discovery.
jobs = [ProxmoxToNautobot]
