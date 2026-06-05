"""App declaration for nautobot_ssot."""

import logging
from importlib import metadata
from nautobot.extras.plugins import NautobotAppConfig
from nautobot_ssot.integrations.utils import each_enabled_integration_module

from .config import ProxmoxConfig

logger = logging.getLogger("nautobot.ssot.proxmox")
__version__ = metadata.version(__name__)

from dataclasses import MISSING

required_settings = [
    field.name for field in ProxmoxConfig.__dataclass_fields__.values()
    if field.default is MISSING and field.default_factory is MISSING
]

class ProxmoxSSOTAppConfig(NautobotAppConfig):
    """App configuration for the nautobot_ssot app."""

    name = "nautobot_ssot_proxmox"
    verbose_name = "Proxmox -> Nautobot"
    version = __version__
    author = "HarbourHeading"
    description = "Sync proxmox to nautobot or vice versa"
    required_settings = required_settings
    default_settings = {}
    config_view_name = "plugins:nautobot_ssot_proxmox:config"
    docs_view_name = "plugins:nautobot_ssot_proxmox:docs"
    searchable_models = ["sync"]

    def ready(self):
        """Trigger callback when the database is ready."""
        super().ready()
        for module in each_enabled_integration_module("signals"):
            logger.debug("Registering signals for %s", module.__file__)
            module.register_signals(self)


config = ProxmoxSSOTAppConfig  # pylint:disable=invalid-name