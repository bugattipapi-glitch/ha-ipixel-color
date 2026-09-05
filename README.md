# iPIXEL Color - Home Assistant Integration

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/A4747U9)

A Home Assistant custom integration for iPIXEL Color LED matrix displays via Bluetooth.
These displays have been recently available as B.K. Light LED Pixel Board from Action and thus get increasing popularity.

## Features

- **Multiple Display Modes**: Text Image (PIL rendering), Native Text, and Clock modes
- **RGB Color Support**: Separate text and background colors via RGB light entities
- **Clock Display**: 9 different clock styles with automatic time synchronization
- **Rich Text Display**: Custom fonts, sizes, multiline text with `\n`, antialiasing
- **Template Support**: Use Home Assistant variables like `{{ states('sensor.temperature') }}°C`
- **Font Management**: Load TTF/OTF fonts from `fonts/` folder
- **Brightness Control**: Adjustable display brightness (1-100)
- **Auto/Manual Updates**: Choose automatic updates or manual refresh
- **State Persistence**: Settings preserved across HA restarts
- **Bluetooth Proxy Support**: Compatible with Bluetooth proxy devices
- **Auto-discovery**: Finds iPIXEL devices automatically via Bluetooth
- **Safe GIF/PNG Playback**: Display bounded public HTTPS media without writing hardware slots

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on the three dots in the top right corner
3. Select **Custom repositories**
4. Add the repository URL: `https://github.com/bugattipapi-glitch/ha-ipixel-color`
5. Select **Integration** as the category
6. Click **Add**
7. Search for "iPIXEL Color" in HACS and install it
8. Restart Home Assistant
9. Add the integration via Settings → Devices & Services → Add Integration

### Manual Installation

1. Copy `custom_components/ipixel_color` to your HA `custom_components` directory
2. Restart Home Assistant
3. Add integration via Settings → Devices & Services → Add Integration

### Optional: Custom Fonts

Place `.ttf`/`.otf` font files in the `fonts/` folder within the integration directory for additional font options.

## Entities

Once configured, you'll get these entities:

**Display Control:**
- `select.{device}_mode` - Display mode (textimage, text, clock)
- `text.{device}_display` - Enter text with templates and `\n` for newlines
- `switch.{device}_power` - Turn display on/off
- `number.{device}_brightness` - Display brightness level (1-100)

**Text Appearance:**
- `select.{device}_font` - Choose from available fonts
- `number.{device}_font_size` - Font size (0=auto, supports decimals like 12.5)
- `number.{device}_line_spacing` - Spacing between lines (0-20px)
- `switch.{device}_antialiasing` - Smooth vs sharp text
- `light.{device}_text_color` - RGB text color
- `light.{device}_background_color` - RGB background color

**Clock Mode:**
- `select.{device}_clock_style` - Clock style (0-8)
- `switch.{device}_clock_24h_format` - 24-hour time format
- `switch.{device}_clock_show_date` - Show date below time

**Update Control:**
- `switch.{device}_auto_update` - Auto-update on changes
- `button.{device}_update_display` - Manual refresh

**Device Info:**
- `sensor.{device}_width` - Display width in pixels
- `sensor.{device}_height` - Display height in pixels
- `sensor.{device}_device_type` - Device model information

## Template Examples

```jinja2
Time: {{ now().strftime('%H:%M') }}
Temp: {{ states('sensor.temperature') | round(1) }}°C
{% if is_state('sun.sun', 'above_horizon') %}Day{% else %}Night{% endif %}
```

## Quick Start

**GIF/PNG Media:**
1. Call `ipixel_color.display_media`
2. Select the iPIXEL device
3. Provide a direct public HTTPS PNG or GIF URL
4. Choose `fit` or `crop`

Media playback is deliberately unslotted (`save_slot=0`). The service rejects
redirects, private-network targets, oversized files, excessive frame counts,
and overlong loops. See [MEDIA-SERVICE.md](MEDIA-SERVICE.md) for the complete
safety limits and examples.

**Fixed-header ticker:**
1. Call `ipixel_color.display_ticker`
2. Select the iPIXEL device
3. Provide a short fixed `header` and a longer `ticker`
4. Optionally set six-character RGB colors and frame duration

The ticker is rendered locally as a 32x32 GIF with a fixed top line and a
large single-line scrolling lower band. It is also unslotted and limited to
32 frames.

**Watched-team events:**
1. Call `ipixel_color.poll_team_feed` against a small public HTTPS JSON feed.
2. Use `pregame` mode to emit the current weekend's scheduled games.
3. Use `score` mode on a short interval to emit one event after a score settles.

The first score poll seeds silently. Later increases settle for 25 seconds so
a touchdown and its conversion become one event; a late conversion-only update
within two minutes is suppressed. The service emits only local Home Assistant
events and never exposes Home Assistant to the public feed.

**Text Mode:**
1. Select mode: `textimage` (for RGB colors) or `text` (native)
2. Set text: `"Hello\nWorld"`
3. Choose text and background colors using light entities
4. Select font and size (or use auto-sizing)
5. Toggle auto-update ON or use manual update button

**Clock Mode:**
1. Select mode: `clock`
2. Choose clock style (0-8)
3. Set 24-hour format and date display preferences
4. Time syncs automatically

**Templates:**
- Templates update automatically with sensor changes when auto-update is ON

## Font Management

- Place `.ttf`/`.otf` files in `fonts/` folder
- Restart HA to see new fonts in dropdown
- Recommended: pixel fonts like 5x5.ttf, 7x7.ttf

## Troubleshooting

- Enable debug logging: `custom_components.ipixel_color: debug`
- Check auto-update is ON or use manual update button
- Verify templates in Developer Tools → Template
- Ensure device is in Bluetooth range

## Status

| Feature | Status |
|---------|--------|
| ✅ Text Display (3 modes) | Complete |
| ✅ RGB Colors | Complete |
| ✅ Clock Mode (9 styles) | Complete |
| ✅ Custom Fonts | Complete |
| ✅ Templates | Complete |
| ✅ State Persistence | Complete |
| ✅ Brightness Control | Complete |
| ✅ Bounded remote GIF/PNG playback | Complete |
| ✅ Fixed-header local ticker | Complete |
| 🔄 Animated Variable-Width Fonts | Planned |

## Technical

- Requires: Home Assistant 2024.1+ and HACS

## Acknowledgments

Special thanks to the authors of [pypixelcolor](https://github.com/lucagoc/pypixelcolor) for their excellent library that powers the core functionality of this integration. Their work in reverse-engineering the iPIXEL protocol has been invaluable.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
