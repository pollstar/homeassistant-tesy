# Home Assistant Tesy integration

Local control of Tesy Wi-Fi water heaters (ESP32 module, "Cloud" series) from Home Assistant — no cloud, no MyTESY account needed — plus a ready-made thermostat card.

This fork by [Pavel Starovoitov (@pollstar)](https://github.com/pollstar) builds on the integration by [@krasnoukhov](https://github.com/krasnoukhov) and [@artin961](https://github.com/artin961) and adds:

- **Weekly programs P1–P3**: read and write them from Home Assistant (`tesy.set_schedule`), with the correct target temperature while a program runs.
- **Thermostat card** `custom:tesy-boiler-card`, shipped with the integration: setpoint dial, modes, Boost, power, schedule editor and diagnostics.
- **Clock and time zone sync** with Home Assistant, so programs switch at the right hour.
- **Configurable poll interval** and an immediate re-read after every command, so changes made on the heater panel or in MyTESY show up quickly.

## Supported devices

Water heaters with the ESP32 Wi-Fi module (black PCB) and its local API at `http://<heater-ip>/api`. Older devices with an Atheros AR9331 module use a different API; enable *Use old API* in the setup dialog for them (basic control only), or replace the module with the ESP32 one.

| ID | Model | Range |
|----|-------|-------|
| 2000 | ModEco | 15–75 °C |
| 2002 | BelliSlimo | 0–4 showers |
| 2003 | BiLight Smart | 15–75 °C |
| 2004 | ModEco 2 | 15–75 °C |
| 2005 | BelliSlimo Lite | 0–4 showers |

Tested with:

- Tesy ModEco Cloud GCV 100 47 24D C22 ECW (ModEco 2, id 2004, firmware 200407 / Wi-Fi 0.29) — weekly programs, card, time zone sync
- [Tesy ModEco Cloud GCV 150 47 24D C22 ECW](https://tesy.com/products/electric-water-heaters/modeco-series/modeco-cloud/?product=gcv-1504724d-c22-ecw)
- BiLight Smart, BelliSlimo
- [Tesy BelliSlimo Cloud GCR 80 27 22 E31 ECW](https://tesy.com/products/electric-water-heaters/bellislimo-series/bellislimo-cloud/?product=gcr-80-27-22-e31-ecw)

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories** → `https://github.com/pollstar/homeassistant-tesy`, category **Integration**.
2. Find **Tesy** in HACS → **Download**.
3. Restart Home Assistant.
4. **Settings → Devices & services → Add integration → Tesy**: enter the heater's IP address and the heater power from its label (e.g. 2400 W). Give the heater a fixed IP on your router.

If the original Tesy integration was installed from HACS, remove it from HACS first; the configured device and its entities stay, since both use the `tesy` domain.

### Manual

Copy `custom_components/tesy/` to `<config>/custom_components/` and restart Home Assistant.

## Options

**Settings → Devices & services → Tesy → Configure**

| Option | Default | Description |
|--------|---------|-------------|
| Poll interval | 30 s | How often the heater is read (5–300 s). Changes made on the heater panel or in MyTESY reach Home Assistant within this time; 10 s is a good value for a local device. |

After every command sent from Home Assistant the heater is read again about 2 s later, so the heating state and target follow right away.

## Thermostat card

The card is served and loaded by the integration — nothing else to install. After installing or updating the integration, restart Home Assistant and reload the browser once (Ctrl+F5; in the companion app: Settings → Debugging → Clear frontend cache).

Add it from **Add card → Tesy boiler**, or with YAML:

```yaml
type: custom:tesy-boiler-card
entity: water_heater.boiler_modeco_2_heater
# optional
name: Boiler
subtitle: ModEco 2 · 100 L
animation: auto     # auto (off when the system asks for reduced motion) | always | off
auto_reload: true   # reload a page that still runs an older card after an update
```

- **Dial** with the current water temperature and the active target. In manual mode a handle on the dial sets the setpoint (15–75 °C); other modes show the target they work to.
- **Power** button at the top right of the dial; **modes** Manual, P1–P3, Eco Smart/Comfort/Night; **Boost**, **schedule** and **statistics** as icon buttons.
- Heating status (heating / target reached / heating off / off) with a subtle animation while the element heats.
- **Schedule** dialog: P1–P3 as a 7×24 grid on wide screens, day by day on phones and portrait screens. Paint hours with a 15–75 °C brush or ❄ (heating off), copy a day to other days, then write to the heater. The dialog follows changes made elsewhere while nothing is edited.
- **Statistics** dialog: energy, errors, Wi-Fi, uptime, firmware, clock state.
- Follows the Home Assistant light/dark theme; English, Russian and Ukrainian.

Related entities (Boost switch, energy and diagnostic sensors, clock sensor, time zone button) are found automatically on the same device.

**Updates and caching.** The card is served with `Cache-Control: no-cache` and an ETag, so browsers and reverse proxies (Cloudflare, nginx) check for a newer file on every page load. A page opened before Home Assistant restarted with a new card (a wall tablet, say) reloads itself once; if that does not help, the card shows a reload banner. A page that never loaded the card needs one manual reload.

## Entities

### Water heater

`water_heater.<name>_heater` — current temperature, target temperature and operation mode.

| Mode | Device `mode` | Description |
|------|---------------|-------------|
| Off | — | Heater powered off (frost protection stays active) |
| Manual (`performance`) | 0 | Heats to the manual setpoint |
| Program 1–3 (`p1`–`p3`) | 1–3 | Weekly program |
| Eco Smart / Eco Comfort / Eco Night (`eco`, `ec2`, `ec3`) | 4–6 | Self-learning modes; the heater picks the target |

Setting a temperature switches the heater to Manual. The target shown is the one the heater works to now: the manual setpoint, the program value for the current hour, the Eco target, or 75 °C while Boost is on.

Attributes: `is_heating`, and on devices with weekly programs:

| Attribute | Description |
|-----------|-------------|
| `schedule_p1` … `schedule_p3` | `{"mo": [24 values], …, "su": [...]}`: °C per hour from 00:00; `14` = heating off for that hour (❄ in MyTESY), `null` = no entry. Not stored in history. |
| `active_program` | `1`–`3` while a program runs, otherwise `null` |
| `manual_temperature` | Setpoint kept for manual mode |

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| Temperature | Water temperature (showers on BelliSlimo) | °C |
| Target temperature | Target the heater works to now | °C |
| Energy consumed | Total energy, accumulated from the heating state × configured power | kWh |
| Energy consumed (resettable) | Energy since the device counter was last reset | kWh |
| Ready in | Minutes until the target is reached (if reported) | min |
| Error status | `00` = no error; E01/E02 lower sensor open/short, E03/E04 upper sensor open/short | — |
| Wi-Fi signal | Module RSSI | dBm |
| Uptime | Module uptime | s |

### Switches, buttons, binary sensors

| Entity | Description |
|--------|-------------|
| Boost | One-time heating to 75 °C, then back to the current mode |
| Child lock | Locks the heater panel (if supported) |
| Reset consumed energy | Resets the resettable energy counter |
| Sync time zone | Writes Home Assistant's time zone to the heater now |
| Clock problem | On if the heater's time zone differs from Home Assistant's or its clock is more than 5 minutes off. Attributes: `problems`, `device_time`, `offset_seconds`, `timezone`, `expected_timezone` |

## Weekly programs

Write 24 hourly temperatures to one or more days of a program:

```yaml
action: tesy.set_schedule
target:
  entity_id: water_heater.boiler_modeco_2_heater
data:
  program: 3
  days: [mo, tu, we, th, fr]   # optional, all days if omitted
  temperatures: [14, 14, 14, 14, 14, 14, 60, 60, 60, 14, 14, 14, 14, 14, 14, 14, 14, 14, 60, 60, 60, 60, 14, 14]
```

Use 15–75 for a setpoint, `14` to switch heating off for that hour, `null` for an hour without an entry. The card's schedule dialog uses this action.

## Clock and time zone

Programs run on the heater's own clock. The module takes UTC from the network and converts it to local time with a POSIX time zone string (`tz`); the time itself cannot be set over the API. The integration writes Home Assistant's time zone to the heater on start-up and whenever it changes in Home Assistant, if they differ. If the *Clock problem* sensor is on while the time zone is right, the module has no internet: restore the connection or set the time on the heater panel (hold **i** in standby).

## Local API

The integration talks to `http://<heater-ip>/api`. Everything is read with one request, `?name=_all`; values are written with `?name=<field>&set=<value>`.

| Field | Description | Write |
|-------|-------------|-------|
| `pwr` | Power | `0` / `1` |
| `mode` | Operation mode (see above) | `0`–`6` |
| `tmpT` | Manual setpoint | `15`–`75` |
| `tmpR` | Active target (placeholder `9` while a program runs without Boost) | — |
| `tmpC` | Water temperature / showers | — |
| `ht` | Heating element on | — |
| `bst` | Boost | `0` / `1` |
| `lck` | Child lock | `0` / `1` |
| `prgP{1-3}{MO..SU}` | Weekly program day: 24 bytes hex, °C per hour, `0E` = off, `FF` = empty | 48 hex chars |
| `tz` | POSIX time zone | string |
| `date` | Device local time (only in `_all`) | — |
| `err` | Error code | — |
| `cdt` | Minutes until ready | — |
| `pwc_t` | Heating element run time, s (updated by the firmware about hourly) | — |
| `pwc_u` | Resettable run time counter | `0` = reset |
| `wdBm`, `wup` | Wi-Fi RSSI, uptime | — |
| `id`, `MAC`, `wsw`, `hsw` | Device type, MAC, firmware versions | — |
| `tmpMX`, `parNF` | Max showers, extra parameters (BelliSlimo, double tank) | — |

Note: `_all` also returns the MyTESY account e-mail and the Wi-Fi SSID without authentication; keep the heater on a trusted network or an IoT VLAN.

## Translations

Entities, modes and setup: English, Bulgarian, German, French, Dutch, Spanish, Italian, Russian, Turkish, Ukrainian. Options, the `set_schedule` action, the clock entities and the card: English, Russian and Ukrainian (other languages fall back to English).

## Development

```bash
python -m unittest discover -s tests   # integration helpers
node --test tests/js/card.test.mjs     # card helpers
```

## Credits

- Original integration: [Dmitry Krasnoukhov (@krasnoukhov)](https://github.com/krasnoukhov) and [@artin961](https://github.com/artin961).
- Weekly programs, thermostat card, time zone sync and poll options: [Pavel Starovoitov (@pollstar)](https://github.com/pollstar).
