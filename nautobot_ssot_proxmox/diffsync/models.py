"""DiffSync models for Proxmox -> Nautobot"""
import random
from typing import Annotated, Optional, List, TypedDict

from django.contrib.contenttypes.models import ContentType
from nautobot.core.choices import ColorChoices
from nautobot.extras.models import Tag
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.virtualization.models import Cluster as NBCluster, VMInterface, VirtualMachine
from nautobot.virtualization.models import VirtualMachine as NBVM
from nautobot_ssot.contrib import CustomFieldAnnotation
from nautobot_ssot.contrib import NautobotModel
from nautobot_ssot.contrib.typeddicts import TagDict


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
      - disk (GB)
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
        "disk",
        "status__name",
        "cluster__name",
        "proxmox_node",
        "proxmox_type",
        "hostname",
        "tags",
    )

    proxmox_vmid: Annotated[str, CustomFieldAnnotation(key="proxmox_vmid")]
    name: str
    vcpus: int
    memory: int
    disk: int
    status__name: str
    cluster__name: str
    proxmox_node: Annotated[Optional[str], CustomFieldAnnotation(key="proxmox_node")] = None
    proxmox_type: Annotated[Optional[str], CustomFieldAnnotation(key="proxmox_type")] = None
    hostname: Annotated[Optional[str], CustomFieldAnnotation(key="hostname")] = None
    tags: List[TagDict] = []


class NamespaceModel(NautobotModel):
    """Shared data model representing a Namespace in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _model = Namespace
    _modelname = "namespace"
    _identifiers = ("name",)
    _attributes = ("description", "tags")

    name: str
    description: Optional[str] = ""
    tags: List[TagDict] = []


class PrefixModel(NautobotModel):
    """Shared data model representing a Prefix in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _model = Prefix
    _modelname = "prefix"
    _identifiers = ("network", "prefix_length", "namespace__name")
    _attributes = ("description", "status__name", "tags")

    # Data type declarations for all identifiers and attributes
    network: str
    namespace__name: str
    prefix_length: int
    status__name: str
    description: Optional[str]
    tags: List[TagDict] = []


class VMInterfaceDict(TypedDict):
    """TypedDict for virtualization VMInterfaces."""

    name: str
    virtual_machine__name: str


class IPAddressModel(NautobotModel):
    """Shared data model representing an IPAddress in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _model = IPAddress
    _modelname = "ipaddress"
    _identifiers = ("host", "mask_length", "parent__network", "parent__prefix_length", "parent__namespace__name")
    _attributes = ("status__name", "vm_interfaces", "tags")

    # Data type declarations for all identifiers and attributes
    host: str
    mask_length: int
    parent__network: str
    parent__prefix_length: int
    parent__namespace__name: str
    status__name: str
    vm_interfaces: List[VMInterfaceDict] = []
    tags: List[TagDict] = []


class InterfaceModel(NautobotModel):
    """Shared data model representing a VMInterface in either of the local or remote Nautobot instances."""

    # Metadata about this model
    _model = VMInterface
    _modelname = "interface"
    _identifiers = ("name", "virtual_machine__name")
    _attributes = (
        "description",
        "enabled",
        "status__name",
        "tags",
    )

    # Data type declarations for all identifiers and attributes
    virtual_machine__name: str
    description: Optional[str]
    enabled: bool
    name: str
    status__name: str
    tags: List[TagDict] = []


class TagModel(NautobotModel):
    """Tag Diffsync model."""

    _model = Tag
    _modelname = "tag"
    _identifiers = ("name",)
    _attributes = ("description",)
    _children = {}

    name: str
    description: Optional[str] = ""

    @classmethod
    def create(cls, adapter, ids, attrs):
        """Create Tag in Nautobot from the NautobotTag object."""
        _color = random.choice(ColorChoices.values())
        _new_tag = Tag(
            name=ids["name"],
            color=_color,
            description=attrs.get("description", ""),
        )
        _new_tag.validated_save()
        _new_tag.content_types.set([ContentType.objects.get_for_model(VirtualMachine)])
        _new_tag.validated_save()
        return super().create(adapter=adapter, ids=ids, attrs=attrs)

    def update(self, attrs):
        """Update Tag in Nautobot from the NautobotTag object."""
        _update_tag = Tag.objects.get(name=self.name)
        if attrs.get("description"):
            _update_tag.description = attrs["description"]
        _update_tag.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Tag in Nautobot from the NautobotTag object."""
        try:
            _tag = Tag.objects.get(name=self.name)
            super().delete()
            _tag.delete()
            return self
        except Tag.DoesNotExist:
            pass

    @classmethod
    def get_queryset(cls):
        """Return the queryset for the model."""
        return cls._model.objects.all()