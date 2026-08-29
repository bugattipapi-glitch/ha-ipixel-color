# iPIXEL remote-media extension

This branch adds two Home Assistant actions to the v0.2.0 integration:

- `ipixel_color.display_media` downloads and displays a public HTTPS PNG or GIF.
- `ipixel_color.show_slot` displays content already stored in a device slot.

The first physical test must use `display_media`. It always sends with
`save_slot=0`; it does not write the panel's flash storage. The underlying
device-library documentation warns that corrupt slot data can cause device
boot loops, so adding a save-to-slot action is deliberately deferred until an
unslotted GIF has been physically verified on device type 129 / 32x32.

## Safety limits

- HTTPS only; credentials, redirects, local hostnames, and non-public IPs are rejected.
- PNG and GIF only.
- Maximum download size: 2 MB.
- Maximum frames: 32.
- Maximum animation-loop duration: 20 seconds.
- Maximum decoded pixel budget: 16 million pixels.
- Successful downloads are cached in memory for one hour.

## First test action

```yaml
action: ipixel_color.display_media
data:
  device_id: de67589f86b3f23970239fcd778876af
  url: https://HOST/dancing-banana-32.gif
  fit: fit
```

Keep the iPixel Color phone app fully closed while Home Assistant controls the
display. If the first unslotted animation is healthy, a separate follow-up can
add carefully bounded slot-writing support.

## Included 32x32 test scenes

This fork includes four original, device-sized GIFs under `assets/`:

- `dancing-banana-32.gif`
- `desert-weather-32.gif`
- `too-hot-32.gif`
- `neon-drive-32.gif`

Their raw public URLs are suitable for bounded Home Assistant tests. They are
small, four-frame loops and are never written to a hardware slot.
