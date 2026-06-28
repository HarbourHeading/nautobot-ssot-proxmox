"""Target (Nautobot) adapter"""
from nautobot_ssot.contrib import NautobotAdapter

from nautobot_ssot_proxmox.diffsync.models import ClusterModel, VirtualMachineModel, InterfaceModel, PrefixModel, IPAddressModel, TagModel


class NautobotInventoryAdapter(NautobotAdapter):
    """DiffSync Adapter that loads a model tree from Nautobot."""
    top_level = ("tag", "cluster", "virtualmachine", "interface", "prefix", "ipaddress")

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel
    interface = InterfaceModel
    prefix = PrefixModel
    ipaddress = IPAddressModel
    tag = TagModel