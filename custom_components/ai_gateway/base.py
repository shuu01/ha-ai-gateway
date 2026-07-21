from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

class AIGatewayBaseEntity(Entity):
    """Base AI Gateway entity."""

    _attr_has_entity_name = True

    def __init__(self, entry):
        self.entry = entry

        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AI Gateway",
            manufacturer="AI Gateway",
            model="Mock",
            entry_type=dr.DeviceEntryType.SERVICE,
        )
