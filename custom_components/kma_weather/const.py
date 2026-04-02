from __future__ import annotations

DOMAIN = "kma_weather"
PLATFORMS = ["weather", "sensor"]

CONF_API_KEY = "api_key"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_NX = "nx"
CONF_NY = "ny"
CONF_LOCATION_NAME = "location_name"
CONF_MAX_CONSECUTIVE_FAILURES = "max_consecutive_failures"
CONF_ZONE = "zone_entity_id"
CONF_AREA_NO = "area_no"
CONF_ENV_KIND = "env_kind"
CONF_ENV_API_KEY = "env_api_key"

DEFAULT_NAME = "KMA Weather"
DEFAULT_SCAN_INTERVAL = 600
DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
KMA_API_BASE = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
KMA_LIVING_API_BASE = "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV4"

ATTR_HOURLY_FORECAST = "hourly_forecast"
ATTR_DAILY_FORECAST = "daily_forecast"
ATTR_GRID = "grid"
ATTR_CONSECUTIVE_FAILURES = "consecutive_failures"
ATTR_FAILURE_TOLERANCE = "failure_tolerance"
ATTR_DATA_STALE = "data_stale"

# KMA SKY values
SKY_CLEAR = "1"
SKY_PARTLY_CLOUDY = "3"
SKY_CLOUDY = "4"

# KMA PTY values
PTY_NONE = "0"
PTY_RAIN = "1"
PTY_RAIN_SNOW = "2"
PTY_SNOW = "3"
PTY_SHOWER = "4"
PTY_DRIZZLE = "5"
PTY_RAIN_SNOW_FLURRY = "6"
PTY_SNOW_FLURRY = "7"
