from __future__ import annotations

from typing import Any, override

from homeassistant import config_entries
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import SOURCE_USER
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import (
    CONF_API_KEY,
    CONF_ENDPOINT,
    CONF_MODEL,
    CONF_PROMPT,
    CONF_PROVIDER_TYPE,
    CONF_WEIGHT,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_WEIGHT,
    DOMAIN,
    PROVIDER_TYPES,
    PROVIDER_TYPE_OPENAI_COMPATIBLE,
    SUBTYPE_STT,
)


class AIGatewayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """AI Gateway config flow."""

    VERSION = 2

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="AI Gateway",
            data={},
        )

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            SUBTYPE_STT: STTProviderSubentryFlowHandler,
        }


class STTProviderSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing STT provider subentries."""

    options: dict[str, Any]

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == SOURCE_USER

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a provider subentry."""
        self.options = {}
        return await self.async_step_init(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure an existing provider subentry."""
        self.options = dict(self._get_reconfigure_subentry().data)
        return await self.async_step_init(user_input)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Configure the provider."""
        # abort if entry is not loaded
        if self._get_entry().state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        options = self.options

        if user_input is not None:
            options.update(user_input)
            if self._is_new:
                return self.async_create_entry(
                    title=options[CONF_MODEL],
                    data=options,
                )
            return self.async_update_reload_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                data=options,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_PROVIDER_TYPE,
                            default=PROVIDER_TYPE_OPENAI_COMPATIBLE,
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=PROVIDER_TYPES,
                                translation_key=CONF_PROVIDER_TYPE,
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            CONF_ENDPOINT,
                            default=options.get(CONF_ENDPOINT, DEFAULT_ENDPOINT),
                        ): str,
                        vol.Optional(
                            CONF_API_KEY,
                            default=options.get(CONF_API_KEY, ""),
                        ): str,
                        vol.Required(
                            CONF_MODEL,
                            default=options.get(CONF_MODEL, DEFAULT_MODEL),
                        ): str,
                        vol.Optional(
                            CONF_WEIGHT,
                            default=options.get(CONF_WEIGHT, DEFAULT_WEIGHT),
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=1, max=100, step=1, mode="box"
                            )
                        ),
                        vol.Optional(
                            CONF_PROMPT,
                            description={
                                "suggested_value": options.get(CONF_PROMPT)
                            },
                        ): TextSelector(
                            TextSelectorConfig(
                                multiline=True, type=TextSelectorType.TEXT
                            )
                        ),
                    }
                ),
                options,
            ),
        )
