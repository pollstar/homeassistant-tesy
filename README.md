# Home Assistant Tesy integration

Local control of Tesy Wi-Fi water heaters (ESP32 module, "Cloud" series) from Home Assistant — no cloud, no MyTESY account needed. A matching thermostat card is available separately: [tesy-boiler-card](https://github.com/pollstar/tesy-boiler-card).

This fork by [Pavel Starovoitov (@pollstar)](https://github.com/pollstar) builds on the integration by [@krasnoukhov](https://github.com/krasnoukhov) and [@artin961](https://github.com/artin961) and adds:

- **Weekly programs P1–P3**: read and write them from Home Assistant (`tesy.set_schedule`), with the correct target temperature while a program runs.
- **Clock and time zone sync** with Home Assistant, so programs switch at the right hour.
- **Configurable poll interval** on every model, and on verified models a re-read right after every command, so changes made on the heater panel or in MyTESY show up quickly.

<img src="https://raw.githubusercontent.com/pollstar/tesy-boiler-card/main/docs/card.png" alt="Tesy boiler card, dark and light theme" width="720">

## Supported devices

Water heaters with the ESP32 Wi-Fi module (black PCB) and its local API at `http://<heater-ip>/api`. Older devices with an Atheros AR9331 module use a different API; enable *Use old API* in the setup dialog for them (basic control only), or replace the module with the ESP32 one.

| ID | Model | Range | Extended features |
|----|-------|-------|-------------------|
| 2000 | ModEco | 15–75 °C | — |
| 2002 | BelliSlimo | 0–4 showers | — |
| 2003 | BiLight Smart | 15–75 °C | — |
| 2004 | ModEco 2 | 15–75 °C | weekly programs, time zone sync, read-back after commands |
| 2005 | BelliSlimo Lite | 0–4 showers | — |

**Extended features are enabled per model.** The integration reads the model id (`id`) from the heater; weekly programs, time zone sync and the read-back after commands are switched on only for models where they were verified, and only if the heater reports the fields they need. Every other model keeps the basic behaviour of the original integration: power, modes, setpoint, Boost, sensors. The list lives in [`features.py`](custom_components/tesy/features.py); a model is added there once it has been tested.

The extended features are tested only with:

- Tesy ModEco Cloud GCV 100 47 24D C22 ECW (ModEco 2, id 2004, firmware 200407 / Wi-Fi 0.29)

If you own another model and want to help verify it, open an [issue](https://github.com/pollstar/homeassistant-tesy/issues) with the output of `http://<heater-ip>/api?name=_all` (remove the e-mail and SSID).

The original integration (basic control) was reported working by its authors and users with:

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
| Poll interval | 30 s | How often the heater is read (5–300 s; 30–300 s on the old API, whose module chokes on bursts of requests). Changes made on the heater panel or in MyTESY reach Home Assistant within this time; 10 s is a good value for a local device. |
| Sync the heater time zone with Home Assistant | on | Writes Home Assistant's time zone to the heater on start-up and when it changes (models with time zone sync). Turn it off if Home Assistant's time zone is not the heater's local time: the programs would shift by hours. |

On models with extended features the heater is also read again about 2 s after every command sent from Home Assistant, so the heating state and target follow right away. Other models are read at the poll interval only.

## Thermostat card

The card is a separate HACS repository: **[pollstar/tesy-boiler-card](https://github.com/pollstar/tesy-boiler-card)** (HACS → Custom repositories → type *Dashboard*). It needs the weekly programs of this integration, so it works on the models listed with extended features above.

Up to version 1.7 the card was served by this integration and added to the dashboard resources by itself. On the first start after the update that resource (`/tesy_static/tesy-boiler-card.js`) is removed; install the card from its repository and your dashboards keep working with the same `type: custom:tesy-boiler-card`.

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

Attributes: `is_heating`, and on models with extended features:

| Attribute | Description |
|-----------|-------------|
| `schedule_p1` … `schedule_p3` | `{"mo": [24 values], …, "su": [...]}`: °C per hour from 00:00; `14` = heating off for that hour (❄ in MyTESY), `null` = no entry. Not stored in history. |
| `active_program` | `1`–`3` while a program runs, otherwise `null` |
| `manual_temperature` | Setpoint kept for manual mode |
| `tesy_features` | Extended features enabled for this heater, e.g. `["readback", "schedule", "timezone"]`. Not stored in history. |

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
  days: [mo, tu, we, th, fr]   # optional, all days if omitted or empty
  temperatures: [14, 14, 14, 14, 14, 14, 60, 60, 60, 14, 14, 14, 14, 14, 14, 14, 14, 14, 60, 60, 60, 60, 14, 14]
```

Use 15–75 for a setpoint, `14` to switch heating off for that hour, `null` for an hour without an entry. The [card](https://github.com/pollstar/tesy-boiler-card)'s schedule dialog uses this action.

## Clock and time zone

Programs run on the heater's own clock. The module takes UTC from the network and converts it to local time with a POSIX time zone string (`tz`); the time itself cannot be set over the API. The integration writes Home Assistant's time zone to the heater on start-up and whenever it changes in Home Assistant, if they differ; this can be turned off in the options. Zones whose rules the heater cannot take (switch times before 0:00 or after 24:00, as in America/Nuuk, Asia/Jerusalem, Asia/Gaza) are not synced: set the clock on the panel. If the *Clock problem* sensor is on while the time zone is right, the module has no internet: restore the connection or set the time on the heater panel (hold **i** in standby).

## Local API

The integration talks to `http://<heater-ip>/api`. Everything is read with one request, `?name=_all`; values are written with `?name=<field>&set=<value>`.

| Field | Description | Write |
|-------|-------------|-------|
| `pwr` | Power | `0` / `1` |
| `mode` | Operation mode (see above) | `0`–`6` |
| `tmpT` | Manual setpoint | `15`–`75` |
| `tmpR` | Active target; in a weekly program it may already be the next hour's value (heating ahead), or a placeholder `9` while the heater is idle | — |
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

Entities, modes and setup: English, Bulgarian, German, French, Dutch, Spanish, Italian, Russian, Turkish, Ukrainian. Options, the `set_schedule` action and the clock entities: English, Russian and Ukrainian (other languages fall back to English).

## Development

```bash
python -m unittest discover -s tests
```

## Credits

- Original integration: [Dmitry Krasnoukhov (@krasnoukhov)](https://github.com/krasnoukhov) and [@artin961](https://github.com/artin961).
- Weekly programs, time zone sync, poll options and the [thermostat card](https://github.com/pollstar/tesy-boiler-card): [Pavel Starovoitov (@pollstar)](https://github.com/pollstar).
