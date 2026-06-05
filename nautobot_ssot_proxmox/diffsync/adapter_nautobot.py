"""Target (Nautobot) adapter"""
from nautobot_ssot.contrib import NautobotAdapter
from .models import ClusterModel, VirtualMachineModel


class NautobotInventoryAdapter(NautobotAdapter):
    """
    Autoloader for our Nautobot models.

    'top_level' lists the models to load independently. VirtualMachineModel
    includes 'cluster__name' so created VMs are attached to the cluster.
    """
    top_level = ("cluster", "virtualmachine")

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel