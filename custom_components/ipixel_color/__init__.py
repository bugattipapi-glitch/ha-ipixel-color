"""The iPIXEL Color integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import iPIXELAPI, iPIXELConnectionError, iPIXELTimeoutError
from .const import DOMAIN, CONF_ADDRESS, CONF_NAME
from .media import async_download_media

_LOGGER = logging.getLogger(__name__)

# Platforms supported by this integration
PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.TEXT, Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.BUTTON, Platform.LIGHT]

SERVICE_DISPLAY_MEDIA = "display_media"
SERVICE_SHOW_SLOT = "show_slot"

DISPLAY_MEDIA_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required("url"): cv.url,
        vol.Optional("fit", default="fit"): vol.In(("fit", "crop")),
    }
)

SHOW_SLOT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required("slot"): vol.All(vol.Coerce(int), vol.Range(min=1, max=255)),
    }
)

# Type alias for iPIXEL config entries


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iPIXEL Color from a config entry."""
    address = entry.data[CONF_ADDRESS]
    name = entry.data[CONF_NAME]
    
    _LOGGER.debug("Setting up iPIXEL Color for %s (%s)", name, address)
    
    # Create API instance with hass for Bluetooth proxy support
    api = iPIXELAPI(hass, address)
    
    # Test connection
    try:
        if not await api.connect():
            raise ConfigEntryNotReady(f"Failed to connect to iPIXEL device at {address}")
        
        _LOGGER.info("Successfully connected to iPIXEL device %s", address)
        
        # Get device info for sensors
        await api.get_device_info()
        
    except iPIXELTimeoutError as err:
        _LOGGER.error("Connection timeout to iPIXEL device %s: %s", address, err)
        raise ConfigEntryNotReady(f"Connection timeout: {err}") from err
        
    except iPIXELConnectionError as err:
        _LOGGER.error("Failed to connect to iPIXEL device %s: %s", address, err)
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err
    
    # Store API instance in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = api
    entry.runtime_data = api
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    
    return True


def _api_for_device(hass: HomeAssistant, device_id: str) -> iPIXELAPI:
    """Resolve a Home Assistant device ID to its configured iPIXEL API."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise HomeAssistantError("The selected iPIXEL device does not exist")

    for entry_id in device.config_entries:
        api = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(api, iPIXELAPI):
            return api
    raise HomeAssistantError("The selected device is not an active iPIXEL display")


def _register_services(hass: HomeAssistant) -> None:
    """Register media actions once for all configured iPIXEL devices."""
    if not hass.services.has_service(DOMAIN, SERVICE_DISPLAY_MEDIA):
        async def _display_media(call: ServiceCall) -> None:
            api = _api_for_device(hass, call.data[ATTR_DEVICE_ID])
            image_bytes, extension = await async_download_media(hass, call.data["url"])
            if not await api.display_media(image_bytes, extension, call.data["fit"]):
                raise HomeAssistantError("The iPIXEL display did not accept the media")

        hass.services.async_register(
            DOMAIN,
            SERVICE_DISPLAY_MEDIA,
            _display_media,
            schema=DISPLAY_MEDIA_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SHOW_SLOT):
        async def _show_slot(call: ServiceCall) -> None:
            api = _api_for_device(hass, call.data[ATTR_DEVICE_ID])
            if not await api.show_slot(call.data["slot"]):
                raise HomeAssistantError("The iPIXEL display did not accept the slot command")

        hass.services.async_register(
            DOMAIN,
            SERVICE_SHOW_SLOT,
            _show_slot,
            schema=SHOW_SLOT_SCHEMA,
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading iPIXEL Color integration")
    
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Disconnect from device
        api: iPIXELAPI = hass.data[DOMAIN].pop(entry.entry_id)
        try:
            await api.disconnect()
            _LOGGER.debug("Disconnected from iPIXEL device")
        except Exception as err:
            _LOGGER.error("Error disconnecting from device: %s", err)

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_DISPLAY_MEDIA)
            hass.services.async_remove(DOMAIN, SERVICE_SHOW_SLOT)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
