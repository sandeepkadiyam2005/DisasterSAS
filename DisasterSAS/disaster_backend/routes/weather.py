import os
import os
import math
import random
from hashlib import sha256
from datetime import datetime, timedelta

import requests
from flask import Blueprint, request, jsonify
from auth import require_permission
from extensions import db, socketio
from models import WeatherLog
from services.email_service import send_email_alert
from services.sms_service import send_sms_alert

weather_bp = Blueprint("weather", __name__)
EMAIL_ALERTS_ENABLED = os.environ.get("ENABLE_EMAIL_ALERTS", "false").lower() == "true"
SMS_ALERTS_ENABLED = os.environ.get("ENABLE_SMS_ALERTS", "false").lower() == "true"
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODE_LABELS = {
    0: "clear sky",
    1: "mostly sunny",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "rain showers",
    81: "heavy rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm",
}


def _normalize_city(city):
    return " ".join(part.capitalize() for part in city.strip().split()) or "Unknown"


def _seed(*parts):
    payload = "|".join(str(p) for p in parts)
    return int(sha256(payload.encode("utf-8")).hexdigest()[:12], 16)


def _determine_alert(temperature, humidity, wind_speed, weather_desc):
    desc = weather_desc.lower()
    if temperature > 45:
        return "🔥 Heatwave Warning!"
    if wind_speed > 15:
        return "🌪 Storm Warning!"
    if "rain" in desc:
        return "🌧 Heavy Rain Alert!"
    if humidity > 85:
        return "⚠ Flood Risk Alert!"
    return "No severe weather conditions."


def _safe_request_json(url, params=None, timeout=12):
    response = requests.get(
        url,
        params=params or {},
        timeout=timeout,
        headers={"User-Agent": "DisasterSAS/1.0"},
    )
    response.raise_for_status()
    return response.json()


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        try:
            return datetime.strptime(str(value), "%Y-%m-%dT%H:%M")
        except ValueError:
            return None


def _weather_code_to_description(code):
    try:
        return WEATHER_CODE_LABELS.get(int(code), "clear sky")
    except (TypeError, ValueError):
        return "clear sky"


def _live_city_coords(city):
    data = _safe_request_json(OPEN_METEO_GEOCODE_URL, {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json",
    })
    results = data.get("results") or []
    if not results:
        return None

    result = results[0]
    try:
        return {
            "name": _normalize_city(result.get("name") or city),
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "timezone": result.get("timezone") or "auto",
        }
    except (KeyError, TypeError, ValueError):
        return None


def _build_weather_tips(weather_desc, temperature, humidity, wind_speed):
    desc = str(weather_desc or "").lower()
    temp = float(temperature or 0)
    humidity = float(humidity or 0)
    wind = float(wind_speed or 0)

    tips = []
    if "rain" in desc or "drizzle" in desc or "shower" in desc:
        tips.extend([
            {"icon": "water", "tip": "Carry an umbrella or light rain cover"},
            {"icon": "drive", "tip": "Drive carefully on wet roads"},
        ])
    elif "thunder" in desc or "storm" in desc:
        tips.extend([
            {"icon": "indoor", "tip": "Stay indoors during thunderstorm activity"},
            {"icon": "trip", "tip": "Avoid trees, open fields, and metal poles"},
        ])
    elif temp >= 36:
        tips.extend([
            {"icon": "water", "tip": "Drink more water and limit midday exposure"},
            {"icon": "uv", "tip": "Use sunscreen and a cap outdoors"},
        ])
    elif humidity >= 75:
        tips.extend([
            {"icon": "indoor", "tip": "Prefer ventilated indoor spaces"},
            {"icon": "sleep", "tip": "Keep evening plans flexible if it feels muggy"},
        ])
    else:
        tips.extend([
            {"icon": "trip", "tip": "Good weather for routine outdoor activity"},
            {"icon": "drive", "tip": "Travel conditions are generally manageable"},
        ])

    if wind >= 12:
        tips.append({"icon": "mask", "tip": "Keep loose items secured outdoors"})
    else:
        tips.append({"icon": "allergy", "tip": "Outdoor comfort is relatively stable today"})

    while len(tips) < 6:
        tips.append({"icon": "water", "tip": "Stay hydrated and keep an eye on updates"})

    return tips[:6]


def _live_weather_bundle(city):
    try:
        coords = _live_city_coords(city)
        if not coords:
            return None

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "timezone": coords["timezone"],
            "current_weather": "true",
            "forecast_days": 15,
            "hourly": ",".join([
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "wind_speed_10m",
                "wind_direction_10m",
                "precipitation_probability",
                "precipitation",
                "cloud_cover",
                "weather_code",
                "pressure_msl",
                "visibility",
                "dew_point_2m",
                "uv_index",
            ]),
            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
                "uv_index_max",
            ]),
        }

        data = _safe_request_json(OPEN_METEO_FORECAST_URL, params=params)
        current = data.get("current_weather") or {}
        hourly = data.get("hourly") or {}
        daily = data.get("daily") or {}

        hourly_times = hourly.get("time") or []
        current_time = current.get("time")
        current_idx = hourly_times.index(current_time) if current_time in hourly_times else 0

        def _hourly_value(key, default=None):
            values = hourly.get(key) or []
            if 0 <= current_idx < len(values):
                return values[current_idx]
            return default

        current_temp = float(current.get("temperature", 0) or 0)
        current_wind_kmh = float(current.get("windspeed", 0) or 0)
        current_wind_ms = round(current_wind_kmh / 3.6, 1)
        current_humidity = int(round(_hourly_value("relative_humidity_2m", 0) or 0))
        current_pressure = float(_hourly_value("pressure_msl", 1013) or 1013)
        current_visibility = float(_hourly_value("visibility", 10000) or 10000)
        current_dew_point = float(_hourly_value("dew_point_2m", _dew_point_c(current_temp, current_humidity)) or _dew_point_c(current_temp, current_humidity))
        current_apparent = float(_hourly_value("apparent_temperature", current_temp) or current_temp)
        current_uv = float(_hourly_value("uv_index", 0) or 0)
        weather_code = current.get("weathercode")
        if weather_code is None:
            weather_code = _hourly_value("weather_code", 0)
        weather_desc = _weather_code_to_description(weather_code)

        daily_times = daily.get("time") or []
        daily_max = daily.get("temperature_2m_max") or []
        daily_min = daily.get("temperature_2m_min") or []
        daily_weather = daily.get("weather_code") or []
        daily_sunrise = daily.get("sunrise") or []
        daily_sunset = daily.get("sunset") or []
        daily_uv = daily.get("uv_index_max") or []

        today_label = daily_times[0] if daily_times else None
        today_date = _parse_iso_datetime(today_label).date() if today_label and _parse_iso_datetime(today_label) else datetime.utcnow().date()
        sunrise = daily_sunrise[0] if daily_sunrise else "--:--"
        sunset = daily_sunset[0] if daily_sunset else "--:--"
        daylight_hours = 0
        sunrise_dt = _parse_iso_datetime(sunrise)
        sunset_dt = _parse_iso_datetime(sunset)
        if sunrise_dt and sunset_dt:
            daylight_hours = round((sunset_dt - sunrise_dt).total_seconds() / 3600.0, 2)

        hourly_rows = []
        for idx, ts in enumerate((hourly_times or [])[:30]):
            dt = _parse_iso_datetime(ts)
            if not dt:
                continue
            hourly_rows.append({
                "datetime": ts,
                "day_label": dt.strftime("%A %d %B"),
                "time_label": dt.strftime("%H:%M"),
                "temperature_c": float((hourly.get("temperature_2m") or [])[idx] or 0),
                "condition": _weather_code_to_description((hourly.get("weather_code") or [0])[idx]),
                "rain_chance_pct": int(round((hourly.get("precipitation_probability") or [0])[idx] or 0)),
                "feels_like_c": float((hourly.get("apparent_temperature") or [])[idx] or 0),
                "wind_kmh": float((hourly.get("wind_speed_10m") or [0])[idx] or 0),
                "wind_dir": _compass_from_angle(float((hourly.get("wind_direction_10m") or [0])[idx] or 0)),
                "uv_index": float((hourly.get("uv_index") or [0])[idx] or 0),
                "cloud_cover_pct": int(round((hourly.get("cloud_cover") or [0])[idx] or 0)),
                "rain_amount_mm": float((hourly.get("precipitation") or [0])[idx] or 0),
            })

        daily_rows = []
        for idx, ts in enumerate(daily_times[:15]):
            dt = _parse_iso_datetime(ts)
            if not dt:
                continue
            daily_rows.append({
                "date": ts,
                "display_date": dt.strftime("%d/%m"),
                "condition": _weather_code_to_description((daily_weather or [0])[idx]).title(),
                "high_c": float((daily_max or [current_temp])[idx] if idx < len(daily_max) else current_temp),
                "low_c": float((daily_min or [current_temp])[idx] if idx < len(daily_min) else current_temp),
            })

        air_quality = _offline_report(coords["name"]).get("air_quality")
        report = {
            "city": coords["name"],
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {
                "pressure_hpa": round(current_pressure),
                "visibility_km": round(current_visibility / 1000.0, 1),
                "uv_index": round(current_uv or (daily_uv[0] if daily_uv else 0), 1),
                "uv_risk": _risk_label(int(round(current_uv or (daily_uv[0] if daily_uv else 0) or 0))),
                "sunrise": sunrise,
                "sunset": sunset,
                "daylight_hours": daylight_hours,
            },
            "air_quality": air_quality,
            "lifestyle_tips": _build_weather_tips(weather_desc, current_temp, current_humidity, current_wind_ms),
        }

        return {
            "city": coords["name"],
            "temperature": round(current_temp, 1),
            "humidity": current_humidity,
            "wind_speed": round(current_wind_ms, 1),
            "weather": weather_desc,
            "disaster_alert": _determine_alert(current_temp, current_humidity, current_wind_ms, weather_desc),
            "snapshot": {
                "city": coords["name"],
                "temperature": round(current_temp, 1),
                "humidity": current_humidity,
                "wind_speed": round(current_wind_ms, 1),
                "weather": weather_desc,
            },
            "report": report,
            "today_details": {
                "high_c": float((daily_max or [current_temp])[0] if daily_max else current_temp),
                "low_c": float((daily_min or [current_temp])[0] if daily_min else current_temp),
                "wind_dir": _compass_from_angle(float(current.get("winddirection", 0) or 0)),
                "wind_kmh": round(current_wind_kmh, 1),
                "humidity_pct": current_humidity,
                "dew_point_c": round(current_dew_point, 1),
                "pressure_hpa": round(current_pressure),
                "uv_index": round(current_uv or (daily_uv[0] if daily_uv else 0), 1),
                "visibility_km": round(current_visibility / 1000.0, 1),
                "moon_phase": _moon_phase_name(today_date),
            },
            "hourly_forecast": hourly_rows,
            "daily_forecast": daily_rows,
        }
    except Exception:
        return None


def _offline_snapshot(city):
    now = datetime.utcnow()
    # Rotate every hour so weather changes gradually over time.
    rnd = random.Random(_seed(city.lower(), now.strftime("%Y-%m-%d-%H")))

    profiles = [
        ("clear sky", (24, 36), (35, 58), (2.0, 6.0)),
        ("few clouds", (22, 34), (40, 65), (2.0, 8.5)),
        ("mist", (19, 29), (72, 92), (1.0, 4.5)),
        ("light rain", (21, 31), (70, 92), (4.0, 12.0)),
        ("heavy rain", (22, 33), (82, 98), (6.0, 16.5)),
        ("thunderstorm", (23, 35), (68, 90), (8.5, 20.0)),
        ("hot and dry", (38, 48), (20, 38), (2.5, 8.0)),
    ]

    weather_desc, temp_range, humidity_range, wind_range = profiles[rnd.randrange(len(profiles))]
    temperature = round(rnd.uniform(*temp_range), 1)
    humidity = int(rnd.uniform(*humidity_range))
    wind_speed = round(rnd.uniform(*wind_range), 1)

    return {
        "city": _normalize_city(city),
        "temperature": temperature,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "weather": weather_desc,
    }


def _offline_forecast(city):
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    base_seed = _seed(city.lower(), now.strftime("%Y-%m-%d"))
    base_rnd = random.Random(base_seed)

    base_temp = base_rnd.uniform(23, 37)
    base_humidity = base_rnd.uniform(48, 84)

    forecasts = []
    for i in range(1, 5):
        ts = now + timedelta(hours=3 * i)
        rnd = random.Random(_seed(city.lower(), ts.isoformat()))
        temp = round(base_temp + rnd.uniform(-5, 9), 1)
        humidity = int(max(20, min(99, base_humidity + rnd.uniform(-18, 16))))
        wind = round(max(0.5, rnd.uniform(2, 22)), 1)

        weather_options = [
            "clear sky",
            "few clouds",
            "light rain",
            "heavy rain",
            "thunderstorm",
            "humid conditions",
            "hot and dry",
        ]
        weather_desc = weather_options[rnd.randrange(len(weather_options))]

        forecasts.append({
            "forecast_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "hours_ahead": round((ts - datetime.utcnow()).total_seconds() / 3600, 1),
            "temperature": temp,
            "humidity": humidity,
            "wind_speed": wind,
            "weather": weather_desc,
        })

    return forecasts


def _normalize_score(value, low, high):
    if high <= low:
        return 1
    score = 1 + ((value - low) / (high - low)) * 9
    return int(max(1, min(10, round(score))))


def _risk_label(score):
    if score <= 2:
        return "Very low"
    if score <= 4:
        return "Low"
    if score <= 6:
        return "Moderate"
    if score <= 8:
        return "High"
    return "Very high"


def _aqi_level(score):
    if score <= 2:
        return "Low"
    if score <= 4:
        return "Moderate"
    if score <= 6:
        return "Elevated"
    if score <= 8:
        return "High"
    return "Severe"


def _aqi_guidance(score):
    if score <= 2:
        return "Air quality is good for most people."
    if score <= 4:
        return "Sensitive groups should reduce prolonged outdoor activity."
    if score <= 6:
        return "Consider a mask for long outdoor exposure."
    if score <= 8:
        return "Reduce strenuous outdoor activities."
    return "Avoid outdoor activity where possible."


def _offline_report(city):
    today = datetime.utcnow().date()
    rnd = random.Random(_seed(city.lower(), today.isoformat(), "report"))

    pressure = int(rnd.uniform(997, 1017))
    visibility_km = round(rnd.uniform(3.5, 12.8), 1)
    uv_index = round(rnd.uniform(1.2, 10.5), 1)

    doy = today.timetuple().tm_yday
    daylight_wave = math.sin((2 * math.pi * doy) / 365.0)
    sunrise_hour = 6.25 - (0.45 * daylight_wave) + rnd.uniform(-0.12, 0.12)
    sunset_hour = 18.2 + (0.45 * daylight_wave) + rnd.uniform(-0.12, 0.12)
    daylight_hours = max(10.5, round(sunset_hour - sunrise_hour, 2))

    def _fmt_time(hour):
        whole = int(hour)
        minute = int(round((hour - whole) * 60))
        if minute == 60:
            whole += 1
            minute = 0
        return f"{whole:02d}:{minute:02d}"

    pollutants = [
        {"code": "PM2.5", "name": "Particulate matter < 2.5 microns", "unit": "ug/m3", "value": round(rnd.uniform(15, 120), 2), "low": 0, "high": 150},
        {"code": "PM10", "name": "Particulate matter < 10 microns", "unit": "ug/m3", "value": round(rnd.uniform(28, 180), 2), "low": 0, "high": 220},
        {"code": "NO2", "name": "Nitrogen dioxide", "unit": "ug/m3", "value": round(rnd.uniform(6, 92), 2), "low": 0, "high": 120},
        {"code": "O3", "name": "Ozone", "unit": "ug/m3", "value": round(rnd.uniform(25, 132), 2), "low": 0, "high": 180},
        {"code": "SO2", "name": "Sulfur dioxide", "unit": "ug/m3", "value": round(rnd.uniform(4, 66), 2), "low": 0, "high": 100},
    ]

    for item in pollutants:
        item["score"] = _normalize_score(item["value"], item["low"], item["high"])
        item["level"] = _aqi_level(item["score"])
        item.pop("low", None)
        item.pop("high", None)

    primary = max(pollutants, key=lambda item: item["score"])
    avg_score = sum(item["score"] for item in pollutants) / len(pollutants)
    overall_score = int(round(max(primary["score"] * 0.78, avg_score)))
    overall_score = max(1, min(10, overall_score))

    lifestyle_pool = [
        {"icon": "mask", "tip": "Carry a light mask outdoors"},
        {"icon": "water", "tip": "Drink extra water through the day"},
        {"icon": "indoor", "tip": "Prefer indoor workouts this evening"},
        {"icon": "drive", "tip": "Road visibility is currently acceptable"},
        {"icon": "allergy", "tip": "Pollen sensitivity risk is low"},
        {"icon": "uv", "tip": "Use sunscreen in midday sun"},
        {"icon": "sleep", "tip": "Night air is calmer after 9 PM"},
        {"icon": "trip", "tip": "Short city trips are suitable"},
    ]
    tips = rnd.sample(lifestyle_pool, k=6)

    return {
        "city": _normalize_city(city),
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": {
            "pressure_hpa": pressure,
            "visibility_km": visibility_km,
            "uv_index": uv_index,
            "uv_risk": _risk_label(int(round(uv_index))),
            "sunrise": _fmt_time(sunrise_hour),
            "sunset": _fmt_time(sunset_hour),
            "daylight_hours": daylight_hours
        },
        "air_quality": {
            "index": overall_score,
            "level": _aqi_level(overall_score),
            "summary": _aqi_guidance(overall_score),
            "primary_pollutant": {
                "code": primary["code"],
                "name": primary["name"],
                "value": primary["value"],
                "unit": primary["unit"],
                "score": primary["score"],
                "level": primary["level"]
            },
            "pollutants": pollutants
        },
        "lifestyle_tips": tips
    }


def _offline_daily_forecast(city, days=15):
    start = datetime.utcnow().date()
    seed_key = _seed(city.lower(), start.isoformat(), "15day")
    base = random.Random(seed_key)
    base_high = base.uniform(28, 38)
    base_low = base.uniform(18, 27)
    conditions = ["Sunny", "Partly cloudy", "Cloudy", "Light rain", "Humid", "Windy", "Haze"]

    output = []
    for i in range(days):
        day = start + timedelta(days=i)
        rnd = random.Random(_seed(city.lower(), day.isoformat(), "d"))
        seasonal = math.sin((2 * math.pi * day.timetuple().tm_yday) / 365.0) * 1.6
        high = round(base_high + seasonal + rnd.uniform(-2.8, 3.2), 1)
        low = round(base_low + (seasonal * 0.4) + rnd.uniform(-2.2, 2.4), 1)
        if low > high - 2:
            low = round(high - rnd.uniform(2.2, 4.6), 1)

        output.append({
            "date": day.isoformat(),
            "display_date": day.strftime("%d/%m"),
            "condition": conditions[rnd.randrange(len(conditions))],
            "high_c": high,
            "low_c": low
        })

    return output


def _dew_point_c(temp_c, humidity_pct):
    humidity = max(1.0, min(100.0, float(humidity_pct)))
    return round(temp_c - ((100.0 - humidity) / 5.0), 1)


def _moon_phase_name(day):
    phase_names = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]
    # 29.53-day lunar cycle approximation from a fixed known new moon date.
    base = datetime(2000, 1, 6).date()
    cycle_day = (day - base).days % 29.53
    idx = int((cycle_day / 29.53) * len(phase_names)) % len(phase_names)
    return phase_names[idx]


def _compass_from_angle(angle):
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    pos = int((angle % 360) / 22.5 + 0.5) % 16
    return dirs[pos]


def _hour_condition(hour, rnd):
    if hour < 5:
        return "Partly cloudy"
    if hour < 7:
        return "Cloudy"
    if hour < 11:
        return "Mostly sunny"
    if hour < 16:
        return "Partly cloudy"
    if hour < 20:
        return "Cloudy"
    return "Partly cloudy"


def _offline_hourly_forecast(city, hours=24):
    start = datetime.utcnow().replace(minute=30, second=0, microsecond=0)
    base_seed = _seed(city.lower(), start.strftime("%Y-%m-%d"), "hourly")
    base = random.Random(base_seed)
    baseline = base.uniform(23, 32)
    humidity_base = base.uniform(48, 76)

    rows = []
    for i in range(hours):
        ts = start + timedelta(hours=i)
        rnd = random.Random(_seed(city.lower(), ts.isoformat(), "h"))
        hour = ts.hour
        diurnal = math.sin(((hour - 6) / 24.0) * 2 * math.pi) * 5.6
        temp = round(baseline + diurnal + rnd.uniform(-1.6, 1.8), 1)
        feels_like = round(temp + rnd.uniform(0.2, 2.0), 1)
        humidity = int(max(28, min(96, humidity_base + rnd.uniform(-20, 18))))
        wind_kmh = round(max(2.0, rnd.uniform(4.5, 17.5)), 1)
        wind_angle = rnd.uniform(0, 360)
        uv = 0 if hour < 6 or hour > 18 else max(0, round((1 - abs(hour - 12) / 6) * 11, 1))
        cloud_cover = int(max(6, min(98, rnd.uniform(15, 85))))
        rain_chance = int(max(0, min(95, rnd.uniform(0, 35) + (cloud_cover * 0.2))))
        rain_mm = round(max(0.0, (rain_chance - 55) / 12), 1) if rain_chance > 55 else 0.0
        condition = _hour_condition(hour, rnd)

        rows.append({
            "datetime": ts.isoformat(),
            "day_label": ts.strftime("%A %d %B"),
            "time_label": ts.strftime("%H:%M"),
            "temperature_c": temp,
            "condition": condition,
            "rain_chance_pct": rain_chance,
            "feels_like_c": feels_like,
            "wind_kmh": wind_kmh,
            "wind_dir": _compass_from_angle(wind_angle),
            "humidity_pct": humidity,
            "uv_index": uv,
            "cloud_cover_pct": cloud_cover,
            "rain_amount_mm": rain_mm
        })

    return rows


@weather_bp.route("/weather", methods=["GET"])
@require_permission("weather:view")
def get_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    data = _live_weather_bundle(city)
    if not data:
        snapshot = _offline_snapshot(city)
        alert = _determine_alert(snapshot["temperature"], snapshot["humidity"], snapshot["wind_speed"], snapshot["weather"])
        data = {
            "city": snapshot["city"],
            "temperature": snapshot["temperature"],
            "humidity": snapshot["humidity"],
            "wind_speed": snapshot["wind_speed"],
            "weather": snapshot["weather"],
        }
    else:
        alert = data.get("disaster_alert") or _determine_alert(
            data["temperature"], data["humidity"], data["wind_speed"], data["weather"]
        )

    if alert != "No severe weather conditions.":
        socketio.emit("new_alert", {
            "city": data["city"],
            "alert": alert,
            "temperature": data["temperature"]
        })

        last_alert = WeatherLog.query.filter_by(city=data["city"]) \
            .order_by(WeatherLog.timestamp.desc()).first()

        send_notifications = True
        if last_alert is not None:
            time_difference = datetime.utcnow() - last_alert.timestamp
            if time_difference < timedelta(minutes=30):
                send_notifications = False

        if send_notifications:
            if EMAIL_ALERTS_ENABLED:
                try:
                    send_email_alert(
                        data["city"], alert, data["temperature"], data["humidity"], data["wind_speed"]
                    )
                except Exception:
                    pass

            if SMS_ALERTS_ENABLED:
                try:
                    send_sms_alert(
                        data["city"], alert, data["temperature"], data["humidity"], data["wind_speed"]
                    )
                except Exception:
                    pass

    new_log = WeatherLog(
        city=data["city"],
        temperature=data["temperature"],
        humidity=data["humidity"],
        wind_speed=data["wind_speed"],
        weather=data["weather"],
        disaster_alert=alert
    )
    db.session.add(new_log)
    db.session.commit()

    return jsonify({
        "city": data["city"],
        "temperature": data["temperature"],
        "weather": data["weather"],
        "humidity": data["humidity"],
        "wind_speed": data["wind_speed"],
        "disaster_alert": alert
    })


@weather_bp.route("/weather/logs", methods=["GET"])
@require_permission("weather:logs")
def get_logs():
    logs = WeatherLog.query.order_by(WeatherLog.timestamp.desc()).all()
    return jsonify([
        {
            "id": log.id,
            "city": log.city,
            "temperature": log.temperature,
            "humidity": log.humidity,
            "wind_speed": log.wind_speed,
            "weather": log.weather,
            "alert": log.disaster_alert,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ])


@weather_bp.route("/weather/analytics", methods=["GET"])
@require_permission("weather:analytics")
def analytics():
    logs = WeatherLog.query.all()

    if not logs:
        return jsonify({"message": "No data available"})

    avg_temp = sum(log.temperature for log in logs) / len(logs)
    avg_humidity = sum(log.humidity for log in logs) / len(logs)
    avg_wind = sum(log.wind_speed for log in logs) / len(logs)

    return jsonify({
        "total_records": len(logs),
        "average_temperature": round(avg_temp, 2),
        "average_humidity": round(avg_humidity, 2),
        "average_wind_speed": round(avg_wind, 2)
    })


@weather_bp.route("/weather/cleanup", methods=["DELETE"])
@require_permission("weather:cleanup")
def cleanup():
    threshold = datetime.utcnow() - timedelta(hours=24)
    old_logs = WeatherLog.query.filter(WeatherLog.timestamp < threshold).all()
    count = len(old_logs)

    for log in old_logs:
        db.session.delete(log)
    db.session.commit()

    return jsonify({"message": f"{count} old logs deleted"})


@weather_bp.route("/alerts/recent", methods=["GET"])
@require_permission("alerts:view")
def recent_alerts():
    alerts = WeatherLog.query.filter(
        WeatherLog.disaster_alert != "No severe weather conditions."
    ).order_by(WeatherLog.timestamp.desc()).limit(10).all()

    return jsonify([
        {
            "city": a.city,
            "alert": a.disaster_alert,
            "temperature": a.temperature,
            "humidity": a.humidity,
            "wind_speed": a.wind_speed,
            "timestamp": a.timestamp.isoformat()
        }
        for a in alerts
    ])


@weather_bp.route("/alerts/today", methods=["GET"])
@require_permission("dashboard:view")
def today_alerts():
    start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    alerts = WeatherLog.query.filter(
        WeatherLog.disaster_alert != "No severe weather conditions.",
        WeatherLog.timestamp >= start_of_day,
        WeatherLog.timestamp < end_of_day
    ).order_by(WeatherLog.timestamp.desc()).all()

    return jsonify([
        {
            "city": a.city,
            "alert": a.disaster_alert,
            "temperature": a.temperature,
            "humidity": a.humidity,
            "wind_speed": a.wind_speed,
            "timestamp": a.timestamp.isoformat()
        }
        for a in alerts
    ])


@weather_bp.route("/dashboard/stats", methods=["GET"])
@require_permission("dashboard:view")
def dashboard_stats():
    total_records = WeatherLog.query.count()

    heatwaves = WeatherLog.query.filter(
        WeatherLog.disaster_alert.like("%Heatwave%")
    ).count()

    storms = WeatherLog.query.filter(
        WeatherLog.disaster_alert.like("%Storm%")
    ).count()

    rains = WeatherLog.query.filter(
        WeatherLog.disaster_alert.like("%Rain%")
    ).count()

    floods = WeatherLog.query.filter(
        WeatherLog.disaster_alert.like("%Flood%")
    ).count()

    return jsonify({
        "total_records": total_records,
        "heatwave_alerts": heatwaves,
        "storm_alerts": storms,
        "rain_alerts": rains,
        "flood_alerts": floods
    })


# ── Forecast-based Disaster Prediction (next 3–12 hours) ──────
@weather_bp.route("/weather/forecast", methods=["GET"])
@require_permission("weather:forecast")
def weather_forecast():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    city_name = _normalize_city(city)
    live = _live_weather_bundle(city_name)
    data = live["daily_forecast"] if live and live.get("daily_forecast") else _offline_forecast(city_name)
    predictions = []

    for forecast in data:
        temp = float(forecast.get("temperature") or forecast.get("high_c") or 0)
        humidity = int(forecast.get("humidity") or 0)
        wind_speed = float(forecast.get("wind_speed") or 0)
        weather_desc = str(forecast.get("weather") or forecast.get("condition") or "").lower()
        forecast_time = forecast.get("forecast_time") or forecast.get("date") or ""
        hours_ahead = forecast.get("hours_ahead")
        if hours_ahead is None and forecast_time:
            dt = _parse_iso_datetime(str(forecast_time))
            if dt:
                hours_ahead = round((dt - datetime.utcnow()).total_seconds() / 3600, 1)
            else:
                hours_ahead = 0

        alerts = []

        if "thunderstorm" in weather_desc:
            alerts.append({"type": "⛈ Thunderstorm Warning", "severity": "high"})

        if temp > 45:
            alerts.append({"type": "🔥 Heatwave Warning", "severity": "critical"})
        elif temp > 40:
            alerts.append({"type": "🌡 Extreme Heat Alert", "severity": "high"})

        if wind_speed > 25:
            alerts.append({"type": "🌪 Severe Storm Warning", "severity": "critical"})
        elif wind_speed > 15:
            alerts.append({"type": "💨 Storm Warning", "severity": "high"})

        if "heavy" in weather_desc and "rain" in weather_desc:
            alerts.append({"type": "🌧 Heavy Rain Alert", "severity": "high"})
        elif "rain" in weather_desc:
            alerts.append({"type": "🌦 Rain Expected", "severity": "medium"})

        if humidity > 90 and "rain" in weather_desc:
            alerts.append({"type": "⚠ Flood Risk Alert", "severity": "high"})
        elif humidity > 85:
            alerts.append({"type": "💧 High Humidity Warning", "severity": "medium"})

        if alerts:
            predictions.append({
                "forecast_time": forecast_time,
                "hours_ahead": hours_ahead,
                "temperature": temp,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "weather": weather_desc,
                "alerts": alerts
            })

            socketio.emit("forecast_alert", {
                "city": city_name,
                "forecast_time": forecast_time,
                "hours_ahead": hours_ahead,
                "alerts": [a["type"] for a in alerts]
            })

    return jsonify({
        "city": city_name,
        "total_forecasts_checked": len(data),
        "upcoming_disasters": predictions,
        "message": f"{len(predictions)} potential disaster(s) detected in next hours"
            if predictions else "No severe weather predicted in the next few hours"
    })


@weather_bp.route("/weather/report", methods=["GET"])
@require_permission("weather:view")
def weather_report():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City parameter is required"}), 400

    city_name = _normalize_city(city)
    live = _live_weather_bundle(city_name)
    if live:
        return jsonify({
            "city": live["city"],
            "snapshot": live["snapshot"],
            "report": live["report"],
            "daily_forecast": live["daily_forecast"],
            "hourly_forecast": live["hourly_forecast"],
            "today_details": live["today_details"],
        })

    snapshot = _offline_snapshot(city_name)
    report = _offline_report(city_name)
    forecast = _offline_daily_forecast(city_name, days=15)
    hourly = _offline_hourly_forecast(city_name, hours=30)
    feels_like = round(snapshot["temperature"] + (snapshot["humidity"] / 100.0) * 2.2, 1)
    dew_point = _dew_point_c(snapshot["temperature"], snapshot["humidity"])
    moon_phase = _moon_phase_name(datetime.utcnow().date())
    today_high = max(item["high_c"] for item in forecast[:1]) if forecast else snapshot["temperature"]
    today_low = min(item["low_c"] for item in forecast[:1]) if forecast else snapshot["temperature"]

    return jsonify({
        "city": city_name,
        "snapshot": snapshot,
        "report": report,
        "daily_forecast": forecast,
        "hourly_forecast": hourly,
        "today_details": {
            "feels_like_c": feels_like,
            "high_c": today_high,
            "low_c": today_low,
            "wind_kmh": round(snapshot["wind_speed"] * 3.6, 1),
            "wind_dir": _compass_from_angle(_seed(city_name, "wind-dir") % 360),
            "humidity_pct": snapshot["humidity"],
            "dew_point_c": dew_point,
            "pressure_hpa": report["metrics"]["pressure_hpa"],
            "uv_index": report["metrics"]["uv_index"],
            "visibility_km": report["metrics"]["visibility_km"],
            "moon_phase": moon_phase,
            "sunrise": report["metrics"]["sunrise"],
            "sunset": report["metrics"]["sunset"]
        }
    })
