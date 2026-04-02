# KMA Weather for Home Assistant

한국 기상청(KMA) 단기예보 API 기반 Home Assistant custom integration 입니다.
HACS Custom Repository로 설치할 수 있도록 구성했습니다.

## Implemented

- `getUltraSrtNcst` for current conditions
- `getUltraSrtFcst` for hourly forecast
- `getVilageFcst` for daily forecast summary
- KMA DFS lat/lon -> nx/ny conversion
- Basic HA config flow for API key + coordinates
- Options flow for consecutive API failure tolerance
- Weather entity with hourly/daily forecasts
- KECO-style transient outage handling: keep last good data until failure threshold is exceeded
- `brand/` assets for Home Assistant icon/logo

## Notes

- Do **not** commit your real KMA service key.
- Current config flow requires selecting a Home Assistant `zone` entity.
- The integration reads that zone's latitude/longitude attributes and computes `nx`/`ny` automatically.
- If the selected zone has no coordinates, setup fails clearly.
- Direct `nx`/`ny` and address lookup are now TODOs for advanced setup only.
- API outage handling mirrors the KECO EV charger pattern:
  - default consecutive failure tolerance: `3`
  - configurable in integration options
  - while failures remain below the threshold, the entity keeps the previous good state
  - once the threshold is reached/exceeded, coordinator update fails and the entity becomes unavailable
- During tolerated failures, entity attributes expose:
  - `consecutive_failures`
  - `failure_tolerance`
  - `data_stale`
- Brand/icon assets are stored under `custom_components/kma_weather/brand/` using Home Assistant-style filenames.

## Installation (HACS)

1. HACS → Integrations → menu → **Custom repositories**
2. Add this repository URL and choose category **Integration**
3. Search for **KMA Weather** in HACS and install it
4. Restart Home Assistant
5. Add integration **KMA Weather**
6. Enter:
   - API key
   - location name (optional)
   - a `zone` entity with latitude/longitude attributes

## Release checklist

- Keep `custom_components/kma_weather/manifest.json` `version` in sync with the Git tag/release version.
- Add a GitHub repository description before publishing the repository to HACS.
- Add GitHub topics such as `home-assistant`, `hacs`, `custom-integration`, `weather`, `kma`.
- After pushing a new tag, create a matching GitHub release for that same version.

## Manual installation

1. Copy `custom_components/kma_weather` into your Home Assistant config directory.
2. Restart Home Assistant.
3. Add integration `KMA Weather`.

## Dev smoke check

From the repo root:

```bash
python3 -m compileall custom_components/kma_weather
```

## TODO

- Zone/address lookup UX
- Location/zone search UX
- More complete category mapping (wind bearing, precipitation type nuances, etc.)
- Translations / strings.json / options flow
- Sensor entities for richer HA dashboards
