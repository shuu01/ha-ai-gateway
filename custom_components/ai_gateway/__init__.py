from __future__ import annotations

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryChange,
    SIGNAL_CONFIG_ENTRY_CHANGED,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .runtime import AIGatewayRuntime

PLATFORMS = (
    Platform.CONVERSATION,
    Platform.STT,
    Platform.TTS,
)


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = AIGatewayRuntime(hass, entry)
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def on_entry_changed(change: ConfigEntryChange, changed_entry: ConfigEntry) -> None:
        if change is not ConfigEntryChange.UPDATED:
            return
        if changed_entry.entry_id != entry.entry_id:
            return
        runtime.rebuild()
        runtime.refresh_state()

    entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            SIGNAL_CONFIG_ENTRY_CHANGED,
            on_entry_changed,
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
