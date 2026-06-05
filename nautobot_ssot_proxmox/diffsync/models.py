"""DiffSync models for Proxmox -> Nautobot"""
from typing import Annotated, Optional
from nautobot_ssot.contrib import NautobotModel, CustomFieldAnnotation
from nautobot.virtualization.models import Cluster as NBCluster
from nautobot.virtualization.models import VirtualMachine as NBVM


class ClusterModel(NautobotModel):
    """Represents a Nautobot Cluster.

    Identifiers
      - name: cluster name (must be unique)
    Attributes
      - cluster_type__name: name of ClusterType (we set this from config so create works)
    """
    _model = NBCluster
    _modelname = "cluster"
    _identifiers = ("name",)
    _attributes = ("cluster_type__name",)

    name: str
    cluster_type__name: Optional[str] = None


class VirtualMachineModel(NautobotModel):
    """Represents a Nautobot VirtualMachine.

    Identifiers
      - proxmox_vmid (immutable VMID from Proxmox)

    Attributes we sync
      - name
      - vcpus
      - memory (MB)
      - status__name ("Active" when running, else "Offline")
      - cluster__name (Cluster membership)
      - proxmox_node
      - proxmox_type ("qemu" or "lxc")
    """
    _model = NBVM
    _modelname = "virtualmachine"
    _identifiers = ("proxmox_vmid",)
    _attributes = (
        "name",
        "vcpus",
        "memory",
        "status__name",
        "cluster__name",
        "proxmox_node",
        "proxmox_type",
    )

    proxmox_vmid: Annotated[str, CustomFieldAnnotation(key="proxmox_vmid")]
    name: str
    vcpus: int
    memory: int
    status__name: str
    cluster__name: str
    proxmox_node: Annotated[Optional[str], CustomFieldAnnotation(key="proxmox_node")] = None
    proxmox_type: Annotated[Optional[str], CustomFieldAnnotation(key="proxmox_type")] = None