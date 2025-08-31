"""
Target (Nautobot) adapter.

We use nautobot_ssot.contrib.NautobotAdapter to auto-load from Nautobot
and to auto-handle create/update/delete for our DiffSync models.
"""
from nautobot_ssot.contrib import NautobotAdapter
from .models import ClusterModel, VirtualMachineModel


class NautobotInventoryAdapter(NautobotAdapter):
    """
    Auto-loader for our Nautobot models.

    'top_level' lists the models to load independently. VirtualMachineModel
    includes 'cluster__name' so created VMs are attached to the cluster.
    """
    top_level = ("cluster", "virtualmachine")

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel
