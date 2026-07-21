from skyfield.api import Loader, Topos, Star
from skyfield.data import hipparcos

# Load once at module level, avoids reloading the file on every CelestialObject
_loader = Loader('/home/eddy/Desktop/Telescope-Automation/data')
_planets = _loader('de421.bsp')
_ts = _loader.timescale()

with _loader.open(hipparcos.URL) as f:
    _star_df = hipparcos.load_dataframe(f)
    
class CelestialObject:
    def __init__(self, celestial_body: str):
        self.name = celestial_body.lower()
        self.planets = _planets  
        self.earth = self.planets['earth']
        self.name_map = {
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

        key = self.name_map.get(self.name)
        if key is None:
            raise ValueError(f"Unsupported celestial body: {celestial_body}")
        if isinstance(key, tuple) and key[0] == "star":
            self.cel_body = Star.from_dataframe(_star_df.loc[key[1]])
        else:
            self.cel_body = self.planets[key]
            
        self.ts = _ts  

    def get_time_now(self):
        return self.ts.now()

    def get_location(self, lat: float, lon: float):
        coords = Topos(
            latitude_degrees=lat,
            longitude_degrees=lon
        )
        return self.earth + coords

    # return elevation, azmith
    def get_astrometric_coords(self, coords: tuple[float, float]):
        lat = coords[0]
        lon = coords[1]
        t = self.get_time_now()
        location = self.get_location(lat, lon)
        astrometric = location.at(t).observe(self.cel_body)
        return astrometric.apparent().altaz()