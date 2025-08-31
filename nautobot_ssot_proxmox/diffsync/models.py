"""
DiffSync models for Proxmox -> Nautobot.

We leverage nautobot_ssot.contrib.NautobotModel so we do not have to write
create/update/delete logic for Nautobot. We only need to define identifiers and
attributes that map to the Nautobot ORM models.
"""
from typing import Optional
from nautobot_ssot.contrib import NautobotModel
from nautobot.virtualization.models import Cluster as NBCluster
from nautobot.virtualization.models import VirtualMachine as NBVM


class ClusterModel(NautobotModel):
    """
    Represents a Nautobot Cluster.

    Identifiers:
      - name: cluster name (must be unique)

    Attributes:
      - type__name: name of ClusterType (we set this from config so create works)
    """
    _model = NBCluster
    _modelname = "cluster"
    _identifiers = ("name",)
    _attributes = ("type__name",)

    name: str
    type__name: Optional[str] = None


class VirtualMachineModel(NautobotModel):
    """
    Represents a Nautobot VirtualMachine.

    Identifiers:
      - custom_fields__proxmox_vmid (immutable VMID from Proxmox)

    Attributes we sync:
      - name
      - vcpus
      - memory (MB)
      - status__name ("Active" when running, else "Offline")
      - cluster__name (Cluster membership)
      - custom_fields__proxmox_node
      - custom_fields__proxmox_type ("qemu" or "lxc")
    """
    _model = NBVM
    _modelname = "virtualmachine"
    _identifiers = ("custom_fields__proxmox_vmid",)
    _attributes = (
        "name",
        "vcpus",
        "memory",
        "status__name",
        "cluster__name",
        "custom_fields__proxmox_node",
        "custom_fields__proxmox_type",
    )

    custom_fields__proxmox_vmid: str
    name: str
    vcpus: int
    memory: int
    status__name: str
    cluster__name: str
    custom_fields__proxmox_node: Optional[str] = None
    custom_fields__proxmox_type: Optional[str] = None
