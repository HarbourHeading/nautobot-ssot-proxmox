from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class ProxmoxConfig:
    """Plugin configuration"""
    proxmox_url: str
    proxmox_user: str
    proxmox_token_name: str
    proxmox_token_value: str
    verify_ssl: bool
    cluster_name: str
    cluster_type_name: str
    proxmox_port: Optional[int] = None
    certificate: Optional[Union[str, tuple[str, str]]] = None
    certificate_passphrase: Optional[str] = None
    http_proxy: Optional[str] = ""
    https_proxy: Optional[str] = ""
