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



def get_nakshatra_safe(moon):
    try:
        if moon is None:
            return {"name": None, "pada": None, "error": "Moon not found"}

        result = get_nakshatra(moon)

        if result["name"] is None:
            return {"name": None, "pada": None, "error": "Calculation failed"}

        return result

    except Exception as e:
        return {"name": None, "pada": None, "error": str(e)}


NAKSHATRA_LORDS = [
    "KETU", "VENUS", "SUN", "MOON", "MARS",
    "RAHU", "JUPITER", "SATURN", "MERCURY"
] * 3

DASHA_YEARS = {
    "KETU": 7, "VENUS": 20, "SUN": 6, "MOON": 10,
    "MARS": 7, "RAHU": 18, "JUPITER": 16,
    "SATURN": 19, "MERCURY": 17
}

NAKSHATRA_LIST = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira",
    "Ardra","Punarvasu","Pushya","Ashlesha","Magha",
    "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
    "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha",
    "Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

def calculate_dasha(nakshatra_name):
    try:
        if nakshatra_name not in NAKSHATRA_LIST:
            return []

        index = NAKSHATRA_LIST.index(nakshatra_name)
        sequence = NAKSHATRA_LORDS[index:] + NAKSHATRA_LORDS[:index]

        dasha = []
        age = 0

        for planet in sequence:
            years = DASHA_YEARS.get(planet, 0)

            dasha.append({
                "planet": planet,
                "start_age": age,
                "end_age": age + years
            })

            age += years

        return dasha

    except:
        return []


def extract_facts(planets):
    facts = {}

    try:
        for planet, data in planets.items():
            house = data.get("house")

            if house:
                facts[f"{planet}_house"] = house

        return facts

    except:
        return {}



def love_rules(planets):
    insights = []

    try:
        venus = planets.get("VENUS", {}).get("house")
        moon = planets.get("MOON", {}).get("house")
        saturn = planets.get("SATURN", {}).get("house")

        if venus == 7:
            insights.append("Strong relationship and marriage potential")

        if saturn == 7:
            insights.append("Delay or maturity in relationships")

        if moon == 1:
            insights.append("Emotionally sensitive in love life")

    except:
        pass

    return insights


def career_rules(planets):
    insights = []

    try:
        saturn = planets.get("SATURN", {}).get("house")
        sun = planets.get("SUN", {}).get("house")
        jupiter = planets.get("JUPITER", {}).get("house")

        if saturn == 10:
            insights.append("Career success through discipline")

        if sun == 10:
            insights.append("Leadership qualities in career")

        if jupiter == 10:
            insights.append("Respect and knowledge-driven career")

    except:
        pass

    return insights


def finance_rules(planets):
    insights = []

    try:
        jupiter = planets.get("JUPITER", {}).get("house")
        if jupiter == 2:
            insights.append("Strong wealth accumulation potential")

    except:
        pass

    return insights

def health_rules(planets):
    insights = []

    try:
        saturn = planets.get("SATURN", {}).get("house")
        mars = planets.get("MARS", {}).get("house")

        if saturn == 6:
            insights.append("Health requires discipline and care")

        if mars == 6:
            insights.append("Possibility of minor injuries or inflammation")

    except:
        pass

    return insights

def generate_interpretation(planets):
    return {
        "love": love_rules(planets),
        "career": career_rules(planets),
        "finance": finance_rules(planets),
        "health": health_rules(planets)
    }


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

        planets = get_planet_data(chart)
        nakshatra = get_nakshatra_safe(moon)

        dasha = calculate_dasha(nakshatra["name"]) if nakshatra["name"] else []

        return {
        "basic_info": {
        "sun_sign": sun.sign if sun else None,
        "moon_sign": moon.sign if moon else None,
        "ascendant": asc.sign if asc else None
        },
        "nakshatra": nakshatra,
        "planets": planets,
        "houses": get_houses(chart),
        "dasha": dasha,
        "facts": extract_facts(planets),
        "interpretation": generate_interpretation(planets)
}

    except Exception as e:
        return {
            "error": str(e),
            "type": str(type(e))
        }