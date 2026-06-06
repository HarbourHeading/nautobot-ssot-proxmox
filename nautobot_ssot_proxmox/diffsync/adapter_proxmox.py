"""Source (Proxmox) adapter"""
import os
import ipaddress
from typing import Optional, TYPE_CHECKING
from diffsync import Adapter
from nautobot_ssot.contrib.typeddicts import TagDict

if TYPE_CHECKING:
    from nautobot.extras.jobs import Job
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from ..config import ProxmoxConfig
from nautobot_ssot_proxmox.diffsync.models import ClusterModel, VirtualMachineModel, InterfaceModel, PrefixModel, \
    IPAddressModel, TagModel
from ..utils.certs import handle_p12_cert


class ProxmoxAdapter(Adapter):
    """DiffSync Adapter that loads a model tree from Proxmox.

    'top_level' contains both cluster and virtualmachine as independent roots.
    We relate VMs to a cluster by providing 'cluster__name' on VirtualMachineModel.
    """
    top_level = ["tag", "cluster", "virtualmachine", "interface", "prefix", "ipaddress"]

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel
    interface = InterfaceModel
    prefix = PrefixModel
    ipaddress = IPAddressModel
    tag = TagModel

    def __init__(self, *args, config: ProxmoxConfig, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job: Job = job
        self.config = config
        self._temp_files = []

        host = self.config.proxmox_url
        if host.startswith("https://"):
            host = host[8:]
        elif host.startswith("http://"):
            host = host[7:]

        proxies = {}
        if self.config.http_proxy:
            proxies["http"] = self.config.http_proxy
        if self.config.https_proxy:
            proxies["https"] = self.config.https_proxy

        cert = self.config.certificate
        if isinstance(cert, str):
            cert = handle_p12_cert(cert, self.config.certificate_passphrase)
        elif isinstance(cert, tuple):
            cert = (handle_p12_cert(cert[0], self.config.certificate_passphrase),
                    handle_p12_cert(cert[1], self.config.certificate_passphrase))

        self._temp_files.append(cert)

        try:
            self.proxmox = ProxmoxAPI(
                host=host,
                user=self.config.proxmox_user,
                token_name=self.config.proxmox_token_name,
                token_value=self.config.proxmox_token_value,
                port=self.config.proxmox_port,
                verify_ssl=self.config.verify_ssl,
                cert=cert,
                proxies=proxies,
            )
        except Exception as err:
            raise RuntimeError(f"Failed to connect to Proxmox API at {self.config.proxmox_url}: {err}") from err

    def __del__(self):
        """Clean up temporary files."""
        for temp_file in getattr(self, "_temp_files", []):
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    @staticmethod
    def _status_to_nb(status: Optional[str]) -> str:
        """Map Proxmox status to Nautobot Status names."""
        return "Active" if status == "running" else "Offline"

    def load(self):
        """Build the in-memory DiffSync objects from Proxmox.

        We create exactly one Cluster (name and type from config),
        then create a VirtualMachineModel for every VM/LXC found.
        """

        try:
            vm_resources = self.proxmox.cluster.resources.get(type="vm")
        except ResourceException as err:
            raise RuntimeError(
                f"Proxmox API error: {err.status_code} {err.status_message}. "
                f"Check credentials and permissions. Response: {err.content}"
            ) from err
        except Exception as err:
            raise RuntimeError(f"Proxmox network error: {err}") from err


        ## SETUP CLUSTER

        cluster_name = self.config.cluster_name
        cluster_type = self.config.cluster_type_name or "Proxmox VE"
        cluster_obj = self.cluster(name=cluster_name, cluster_type__name=cluster_type)
        self.add(cluster_obj)

        ## SETUP VMs

        for vm in vm_resources:
            vm_id = str(vm.get("vmid") or "")
            if not vm_id:
                continue

            name = vm.get("name") or f"vm-{vm_id}"
            nb_status = self._status_to_nb(vm.get("status"))
            vcpus = int(vm.get("maxcpu", 0))
            mem_mb = int((vm.get("maxmem", 0)) // (1024 * 1024))  # MB
            disk_max_gb = int((vm.get("maxdisk", 0)) // (1024 * 1024 * 1024)) or 0  # GB
            proxmox_node = vm.get("node") or vm.get("vm")
            vm_type = vm.get("type")  # 'qemu' or 'lxc'

            tags_str = vm.get("tags", "")
            vm_tags: list[TagDict] = [{"name": tag.strip()} for tag in tags_str.split(';') if tag.strip()]

            for tag_dict in vm_tags:
                tag_name = tag_dict.get("name", "")
                if not tag_name:
                    continue

                self.get_or_instantiate(
                    self.tag,
                    {"name": tag_name},
                    {"description": "Imported from Proxmox"},
                )

            complete_vm = self.virtualmachine(
                proxmox_vmid=vm_id,
                name=name,
                vcpus=vcpus,
                memory=mem_mb,
                disk=disk_max_gb,
                status__name=nb_status,
                cluster__name=cluster_name,
                proxmox_node=proxmox_node,
                proxmox_type=vm_type,
                tags=vm_tags,
            )
            self.add(complete_vm)

        ## SETUP PREFIXES, INTERFACES AND IP ADDRESSES

        # Collect all interface and IP data
        vm_network_data = []
        for vm in vm_resources:
            vm_status = vm.get('status')
            if vm_status != 'running':
                continue

            vm_id: str = vm.get('vmid')
            vm_type: str = vm.get('type')
            vm_name: str = vm.get('name') or f"vm-{vm_id}"
            proxmox_node = vm.get("node") or vm.get("vm")

            try:
                if vm_type == 'qemu':
                    interfaces = self.proxmox.nodes(proxmox_node).qemu(vm_id).agent("network-get-interfaces").get()
                else:
                    interfaces = self.proxmox.nodes(proxmox_node).lxc(vm_id).agent("network-get-interfaces").get()
            except ResourceException:
                interfaces = {}
                # Fails if qemu-guest-agent is not installed. Maybe use the below method instead?
                # https://forum.proxmox.com/threads/proxmox-api-check-qemu-installed-and-extract-tags.160885/

            for iface in interfaces.get("result", {}):
                iface_name = iface.get("name", "")
                if iface_name == "lo" or not iface_name:
                    continue

                for addr_info in iface.get("ip-addresses", []):
                    ip_address = addr_info.get("ip-address")
                    prefix_length = addr_info.get("prefix")

                    if not ip_address or prefix_length is None:
                        continue

                    # Skip loopback addresses
                    if ip_address.startswith("127.") or ip_address == "::1":
                        continue

                    try:
                        network = ipaddress.ip_network(f"{ip_address}/{prefix_length}", strict=False)
                        network_str = str(network.network_address)
                        prefix_len = int(prefix_length)
                    except ValueError:
                        continue

                    vm_network_data.append({
                        'vm_name': vm_name,
                        'iface_name': iface_name,
                        'ip_address': ip_address,
                        'prefix_len': prefix_len,
                        'network_str': network_str,
                    })

        prefixes_seen = set()
        for data in vm_network_data:
            prefix_key = (data['network_str'], data['prefix_len'], "Global")
            if prefix_key not in prefixes_seen:
                complete_prefix = self.prefix(
                    network=data['network_str'],
                    namespace__name="Global",
                    prefix_length=data['prefix_len'],
                    status__name="Active",
                    description="",
                    tags=[]
                )
                self.add(complete_prefix)
                prefixes_seen.add(prefix_key)

        interfaces_seen = set()
        for data in vm_network_data:
            iface_key = (data['iface_name'], data['vm_name'])
            if iface_key not in interfaces_seen:
                complete_interface = self.interface(
                    name=data['iface_name'],
                    virtual_machine__name=data['vm_name'],
                    description="",
                    enabled=True,
                    status__name="Active",
                    tags=[]
                )
                self.add(complete_interface)
                interfaces_seen.add(iface_key)

        for data in vm_network_data:
            complete_ip = self.ipaddress(
                host=data['ip_address'],
                mask_length=data['prefix_len'],
                parent__network=data['network_str'],
                parent__prefix_length=data['prefix_len'],
                parent__namespace__name="Global",
                status__name="Active",
                vm_interfaces=[{"name": data['iface_name'], "virtual_machine__name": data['vm_name']}],
                tags=[]
            )

            try:
                self.add(complete_ip)
            except Exception:
                pass
