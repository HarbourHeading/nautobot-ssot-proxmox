"""Source (Proxmox) adapter"""
import os
from typing import Optional

from diffsync import Adapter
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException

from ..config import ProxmoxConfig
from .models import ClusterModel, VirtualMachineModel
from ..utils.certs import handle_p12_cert


class ProxmoxAdapter(Adapter):
    """DiffSync Adapter that loads a model tree from Proxmox.

    'top_level' contains both cluster and virtualmachine as independent roots.
    We relate VMs to a cluster by providing 'cluster__name' on VirtualMachineModel.
    """
    top_level = ["cluster", "virtualmachine"]

    cluster = ClusterModel
    virtualmachine = VirtualMachineModel

    def __init__(self, *args, config: ProxmoxConfig, job=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.job = job
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
            cert = (handle_p12_cert(cert[0], self.config.certificate_passphrase), handle_p12_cert(cert[1], self.config.certificate_passphrase))

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
        cluster_name = self.config.cluster_name
        cluster_type = self.config.cluster_type_name or "Proxmox VE"

        cluster_obj = self.cluster(name=cluster_name, cluster_type__name=cluster_type)
        self.add(cluster_obj)

        try:
            items = self.proxmox.cluster.resources.get(type="vm")
        except ResourceException as err:
            raise RuntimeError(
                f"Proxmox API error: {err.status_code} {err.status_message}. "
                f"Check credentials and permissions. Response: {err.content}"
            ) from err
        except Exception as err:
            raise RuntimeError(f"Proxmox network error: {err}") from err

        for r in items:
            vmid = str(r.get("vmid"))
            if not vmid:
                continue

            name = r.get("name") or f"vm-{vmid}"
            nb_status = self._status_to_nb(r.get("status"))
            vcpus = int(r.get("maxcpu") or 0)
            mem_mb = int((r.get("maxmem") or 0) // (1024 * 1024))  # maxmem is bytes; store MB in Nautobot
            node = r.get("node")
            vmtype = r.get("type")  # 'qemu' or 'lxc'

            vm = self.virtualmachine(
                proxmox_vmid=vmid,
                name=name,
                vcpus=vcpus,
                memory=mem_mb,
                status__name=nb_status,
                cluster__name=cluster_name,
                proxmox_node=node,
                proxmox_type=vmtype,
            )
            self.add(vm)