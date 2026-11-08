"""Config flow for Live Calendar."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import webhook
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    AuthError,
    DiscoveredCalendar,
    SourceError,
    discover_calendars,
    normalize_url,
)
from .const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SOURCE_CALDAV,
    SOURCE_ICS,
)
from .coordinator import InvalidCalendar, parse_ics_texts
from .util import build_source, get_webhook_url, make_auth

_LOGGER = logging.getLogger(__name__)

_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

ICS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_USERNAME): str,
        vol.Optional(CONF_PASSWORD): _PASSWORD,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)

CALDAV_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): _PASSWORD,
        vol.Required(CONF_VERIFY_SSL, default=True): bool,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): _PASSWORD}
)


async def _validate(hass, data: dict[str, Any]) -> None:
    """Fetch and parse once; raises AuthError / SourceError / InvalidCalendar."""
    result = await build_source(hass, data).fetch(force=True)
    await hass.async_add_executor_job(parse_ics_texts, result.texts)


def _error_for(err: Exception) -> str:
    if isinstance(err, AuthError):
        return "invalid_auth"
    if isinstance(err, InvalidCalendar):
        return "invalid_calendar"
    if isinstance(err, SourceError):
        return "cannot_connect"
    _LOGGER.exception("Unexpected error validating calendar", exc_info=err)
    return "unknown"


class LiveCalendarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Live Calendar."""

    VERSION = 1

    def __init__(self) -> None:
        self._conn: dict[str, Any] = {}
        self._discovered: dict[str, DiscoveredCalendar] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the kind of calendar source."""
        return self.async_show_menu(step_id="user", menu_options=["caldav", "ics"])

    # -- ICS URL ---------------------------------------------------------

    async def async_step_ics(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_SOURCE: SOURCE_ICS,
                CONF_URL: normalize_url(user_input[CONF_URL]),
                CONF_USERNAME: user_input.get(CONF_USERNAME) or None,
                CONF_PASSWORD: user_input.get(CONF_PASSWORD) or None,
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            await self.async_set_unique_id(data[CONF_URL])
            self._abort_if_unique_id_configured()
            try:
                await _validate(self.hass, data)
            except Exception as err:  # noqa: BLE001
                errors["base"] = _error_for(err)
            else:
                data[CONF_WEBHOOK_ID] = webhook.async_generate_id()
                return self.async_create_entry(title=user_input[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="ics",
            data_schema=self.add_suggested_values_to_schema(ICS_SCHEMA, user_input),
            errors=errors,
        )

    # -- CalDAV ----------------------------------------------------------

    async def async_step_caldav(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._conn = {
                CONF_SOURCE: SOURCE_CALDAV,
                CONF_USERNAME: user_input[CONF_USERNAME],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
                CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
            }
            session = async_get_clientsession(
                self.hass, verify_ssl=user_input[CONF_VERIFY_SSL]
            )
            try:
                found = await discover_calendars(
                    session,
                    user_input[CONF_URL],
                    make_auth(user_input[CONF_USERNAME], user_input[CONF_PASSWORD]),
                )
            except Exception as err:  # noqa: BLE001
                errors["base"] = _error_for(err)
            else:
                if not found:
                    errors["base"] = "no_calendars"
                else:
                    self._discovered = {c.url: c for c in found}
                    if len(found) == 1:
                        result, error = await self._create_caldav(found[0])
                        if result is not None:
                            return result
                        errors["base"] = error or "unknown"
                    else:
                        return await self.async_step_pick()
        return self.async_show_form(
            step_id="caldav",
            data_schema=self.add_suggested_values_to_schema(CALDAV_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            chosen = self._discovered[user_input["calendar"]]
            result, error = await self._create_caldav(chosen)
            if result is not None:
                return result
            errors["base"] = error or "unknown"
        options = [
            SelectOptionDict(value=c.url, label=c.name) for c in self._discovered.values()
        ]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {vol.Required("calendar"): SelectSelector(SelectSelectorConfig(options=options))}
            ),
            errors=errors,
        )

    async def _create_caldav(
        self, calendar: DiscoveredCalendar
    ) -> tuple[ConfigFlowResult | None, str | None]:
        data = {**self._conn, CONF_URL: calendar.url}
        await self.async_set_unique_id(calendar.url)
        self._abort_if_unique_id_configured()
        try:
            await _validate(self.hass, data)
        except Exception as err:  # noqa: BLE001
            return None, _error_for(err)
        data[CONF_WEBHOOK_ID] = webhook.async_generate_id()
        return self.async_create_entry(title=calendar.name, data=data), None

    # -- Re-authentication ----------------------------------------------

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                await _validate(self.hass, {**entry.data, **user_input})
            except Exception as err:  # noqa: BLE001
                errors["base"] = _error_for(err)
            else:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self.add_suggested_values_to_schema(
                REAUTH_SCHEMA, {CONF_USERNAME: entry.data.get(CONF_USERNAME)}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LiveCalendarOptionsFlow()


class LiveCalendarOptionsFlow(OptionsFlow):
    """Change the polling interval and show the push URL."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            )
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
            description_placeholders={
                "webhook_url": get_webhook_url(
                    self.hass, self.config_entry.data[CONF_WEBHOOK_ID]
                )
            },
        )
