from typing import NamedTuple

from skyfield.api import Loader, Topos, Star
from skyfield.data import hipparcos

import config
from TimeKeeper import time_keeper

# Load once at module level, avoids reloading the file on every CelestialObject
_loader = Loader(str(config.DATA_DIR))
_planets = _loader('de421.bsp')
_ts = _loader.timescale()

with _loader.open(hipparcos.URL) as f:
    _star_df = hipparcos.load_dataframe(f)


class AltAz(NamedTuple):
    """Apparent position in plain-float degrees."""
    altitude: float
    azimuth: float


class CelestialObject:
    NAME_MAP = {
        "mercury": "MERCURY",
        "venus": "VENUS",
        "earth": "EARTH",
        "moon": "MOON",
        "mars": "MARS",
        "jupiter": "JUPITER BARYCENTER",
        "saturn": "SATURN BARYCENTER",
        "uranus": "URANUS BARYCENTER",
        "neptune": "NEPTUNE BARYCENTER",
        "pluto": "PLUTO BARYCENTER",
        "sun": "SUN",
        "polaris": ("star", 11767),
    }

    def __init__(self, celestial_body: str):
        self.name = celestial_body.lower()
        self.planets = _planets
        self.earth = self.planets['earth']

        key = self.NAME_MAP.get(self.name)
        if key is None:
            raise ValueError(f"Unsupported celestial body: {celestial_body}")
        if isinstance(key, tuple) and key[0] == "star":
            self.cel_body = Star.from_dataframe(_star_df.loc[key[1]])
        else:
            self.cel_body = self.planets[key]

        self.ts = _ts

    @property
    def display_name(self) -> str:
        return self.name.capitalize()

    def get_time_now(self):
        # GPS or laptop time when available; the Pi's clock can be wrong offline
        return self.ts.from_datetime(time_keeper.now())

    def get_location(self, lat: float, lon: float):
        coords = Topos(
            latitude_degrees=lat,
            longitude_degrees=lon
        )
        return self.earth + coords

    # Returns AltAz(altitude, azimuth) in degrees as plain floats
    def get_astrometric_coords(self, coords: tuple[float, float]) -> AltAz:
        lat = coords[0]
        lon = coords[1]
        t = self.get_time_now()
        location = self.get_location(lat, lon)
        astrometric = location.at(t).observe(self.cel_body)
        alt, az, _distance = astrometric.apparent().altaz()
        # Skyfield returns numpy values; plain floats keep JSON and maths simple
        return AltAz(float(alt.degrees), float(az.degrees))
