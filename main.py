from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const

import swisseph as swe

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# INPUT MODEL
# -----------------------------
class KundliInput(BaseModel):
    date: str
    time: str
    lat: float
    lon: float
    tz: str


# -----------------------------
# PLANET MAP
# -----------------------------
PLANET_NAME_MAP = {
    const.SUN: "SUN",
    const.MOON: "MOON",
    const.MERCURY: "MERCURY",
    const.VENUS: "VENUS",
    const.MARS: "MARS",
    const.JUPITER: "JUPITER",
    const.SATURN: "SATURN",
    const.NORTH_NODE: "RAHU",
    const.SOUTH_NODE: "KETU"
}


# -----------------------------
# PLANETS
# -----------------------------
def get_planet_data(chart):
    planet_data = {}

    # Get house cusps
    house_cusps = [house.lon for house in chart.houses]

    for planet, name in PLANET_NAME_MAP.items():
        obj = chart.get(planet)
        if not obj:
            continue

        planet_lon = obj.lon
        house_number = None

        # 🔥 Find house manually
        for i in range(12):
            start = house_cusps[i]
            end = house_cusps[(i + 1) % 12]

            if start < end:
                if start <= planet_lon < end:
                    house_number = i + 1
                    break
            else:
                # wrap around case (360°)
                if planet_lon >= start or planet_lon < end:
                    house_number = i + 1
                    break

        planet_data[name] = {
            "sign": obj.sign,
            "degree": round(obj.lon, 2),
            "house": house_number,
            "retrograde": obj.isRetrograde()
        }

    return planet_data


# -----------------------------
# HOUSES (FIXED)
# -----------------------------
def get_houses(chart):
    houses = {}

    try:
        for i, house in enumerate(chart.houses, start=1):
            houses[f"house_{i}"] = {
                "number": i,
                "sign": house.sign,
                "degree": round(house.lon, 2)
            }
    except:
        pass

    return houses


# -----------------------------
# NAKSHATRA (MANUAL CALCULATION)
# -----------------------------
def get_nakshatra(moon):
    try:
        nakshatras = [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
            "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
            "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
            "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
            "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
            "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
        ]

        degree = moon.lon

        nak_index = int(degree / (360 / 27))
        pada = int((degree % (360 / 27)) / (360 / 108)) + 1

        return {
            "name": nakshatras[nak_index],
            "pada": pada
        }

    except:
        return {"name": None, "pada": None}


# -----------------------------
# ROUTES
# -----------------------------
@app.get("/")
def home():
    return {"message": "Kundli API running 🚀"}


@app.post("/kundli")
def generate_kundli(data: KundliInput):
    try:
        # 🔥 REQUIRED
        swe.set_ephe_path('./ephe')

        date = Datetime(data.date, data.time, data.tz)
        pos = GeoPos(data.lat, data.lon)
        chart = Chart(date, pos)

        sun = chart.get(const.SUN)
        moon = chart.get(const.MOON)
        asc = chart.get(const.ASC)

        return {
            "basic_info": {
                "sun_sign": sun.sign if sun else None,
                "moon_sign": moon.sign if moon else None,
                "ascendant": asc.sign if asc else None
            },
            "nakshatra": get_nakshatra(moon),
            "planets": get_planet_data(chart),
            "houses": get_houses(chart)
        }

    except Exception as e:
        return {
            "error": str(e),
            "type": str(type(e))
        }