"""Conversation support for AI Gateway."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .base import AIGatewayBaseEntity
import logging

logger = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AI Gateway conversation."""

    async_add_entities([AIGatewayConversationEntity(entry)])

class AIGatewayConversationEntity(conversation.ConversationEntity, AIGatewayBaseEntity):
    """Mock conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "Conversation"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self.entry = entry

        self._attr_unique_id = f"{entry.entry_id}_conversation"

        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="AI Gateway",
            manufacturer="AI Gateway",
            model="Mock",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def _mock_stream(self, prompt: str):
        logger.warning("LLM received: %s", prompt)

        yield {
            "role": "assistant",
            "content": f"This is a mock llm response. {random.randint(1, 100000)}",
        }

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:

        async for _ in chat_log.async_add_delta_content_stream(
            self.entity_id,
            self._mock_stream(user_input.text),
        ):
            pass

        result = conversation.async_get_result_from_chat_log(
            user_input,
            chat_log,
        )
        logger.warning(f"Conversation result: {result}")
        logger.warning(f"Speech: {result.response.speech}")
        logger.warning(f"Response dict: {result.response.as_dict()}")

        return result
