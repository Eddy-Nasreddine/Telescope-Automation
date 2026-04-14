from skyfield.api import load, Topos

class CelestialObject:
    def __init__(self, celestial_body: str):
        self.name = celestial_body.lower()

        self.planets = load('de421.bsp')
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
        }

        key = self.name_map.get(self.name)
        if key is None:
            raise ValueError(f"Unsupported celestial body: {celestial_body}")

        self.cel_body = self.planets[key]

        self.coords = Topos(
            latitude_degrees=53.62300344381324,
            longitude_degrees=-113.51295247822964
        )

        self.ts = load.timescale()

    def get_time_now(self):
        return self.ts.now()

    def get_location(self):
        return self.earth + self.coords

    def get_astrometric_coords(self):
        t = self.get_time_now()
        location = self.get_location()
        astrometric = location.at(t).observe(self.cel_body)
        return astrometric.apparent().altaz()