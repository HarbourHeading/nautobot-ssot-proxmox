"""Target (Nautobot) adapter"""
from nautobot_ssot.contrib import NautobotAdapter

from nautobot_ssot_proxmox.diffsync.models import ClusterModel, VirtualMachineModel, InterfaceModel, PrefixModel, IPAddressModel, TagModel


class NautobotInventoryAdapter(NautobotAdapter):
    """
    Autoloader for our Nautobot models.

    'top_level' lists the models to load independently. VirtualMachineModel
    includes 'cluster__name' so created VMs are attached to the cluster.
    """
    top_level = ("tag", "cluster", "virtualmachine", "interface", "prefix", "ipaddress")

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel
    interface = InterfaceModel
    prefix = PrefixModel
    ipaddress = IPAddressModel
    tag = TagModel