"""
Remote (source) adapter: reads Proxmox inventory via proxmoxer.

We intentionally keep this minimal:
- One Cluster (from config)
- All VMs and LXC containers listed by /cluster/resources?type=vm
- We record VMID, name, vCPUs, memory (MB), status, node, and type.
"""
from typing import Optional

from diffsync import Adapter
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException
from requests.exceptions import RequestException

from ..const import (
    CFG_PROXMOX_URL,
    CFG_PROXMOX_USER,
    CFG_PROXMOX_TOKEN_NAME,
    CFG_PROXMOX_TOKEN_VALUE,
    CFG_VERIFY_SSL,
    CFG_CLUSTER_NAME,
    CFG_CLUSTER_TYPE_NAME,
)
from .models import ClusterModel, VirtualMachineModel


class ProxmoxAdapter(Adapter):
    """
    DiffSync Adapter that loads a model tree from Proxmox.

    top_level contains both cluster and virtualmachine as independent roots.
    We relate VMs to a cluster by providing 'cluster__name' on VirtualMachineModel.
    """
    top_level = ["cluster", "virtualmachine"]

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel

    def __init__(self, *args, config: dict, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
        self.config = config

        verify_ssl = bool(self.config.get(CFG_VERIFY_SSL, True))

        # ProxmoxAPI host parameter accepts a hostname or URL base without
        # path. For clarity we support full https URL; proxmoxer will handle it.
        try:
            self.proxmox = ProxmoxAPI(
                host=self.config[CFG_PROXMOX_URL],
                user=self.config[CFG_PROXMOX_USER],
                token_name=self.config[CFG_PROXMOX_TOKEN_NAME],
                token_value=self.config[CFG_PROXMOX_TOKEN_VALUE],
                verify_ssl=verify_ssl,
            )
        except RequestException as err:
            raise RuntimeError(f"Failed to connect to Proxmox API at {self.config[CFG_PROXMOX_URL]}: {err}") from err


    @staticmethod
    def _status_to_nb(status: Optional[str]) -> str:
        """
        Map Proxmox status to Nautobot Status names.
        """
        return "Active" if status == "running" else "Offline"

    def load(self):
        """
        Build the in-memory DiffSync objects from Proxmox.

        We create exactly one Cluster (name and type from config),
        then create a VirtualMachineModel for every VM/LXC found.
        """
        cluster_name = self.config[CFG_CLUSTER_NAME]
        cluster_type = self.config.get(CFG_CLUSTER_TYPE_NAME, "Proxmox VE")

        # 1) Cluster
        cluster_obj = self.cluster(name=cluster_name, type__name=cluster_type)
        self.add(cluster_obj)

        # 2) VMs and LXCs from /cluster/resources?type=vm
        try:
            items = self.proxmox.cluster.resources.get(type="vm")
        except ResourceException as err:
            raise RuntimeError(
                f"Proxmox API error: {err.response.status_code} {err.response.reason}. "
                f"Check credentials and permissions. Response: {err.response.text}"
            ) from err
        except RequestException as err:
            raise RuntimeError(f"Proxmox network error: {err}") from err

        for r in items:
            vmid = str(r.get("vmid"))
            if not vmid:
                continue

            name = r.get("name") or f"vm-{vmid}"
            nb_status = self._status_to_nb(r.get("status"))
            vcpus = int(r.get("maxcpu") or 0)
            # maxmem is bytes; store MB in Nautobot
            mem_mb = int((r.get("maxmem") or 0) // (1024 * 1024))
            node = r.get("node")
            vmtype = r.get("type")  # 'qemu' or 'lxc'

            vm = self.virtualmachine(
                custom_fields__proxmox_vmid=vmid,
                name=name,
                vcpus=vcpus,
                memory=mem_mb,
                status__name=nb_status,
                cluster__name=cluster_name,
                custom_fields__proxmox_node=node,
                custom_fields__proxmox_type=vmtype,
            )
            self.add(vm)
