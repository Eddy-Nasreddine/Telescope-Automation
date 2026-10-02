import logging
import threading
import time
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("TimeKeeper")

# The Pi has no internet outside, so its clock can be wrong after a boot.
# Planet positions depend on the time, so astronomy uses the best source we have:
#   1. GPS   - synced from the GPS module (exact)
#   2. laptop - the browser sends its clock when the dashboard opens
#   3. system - the Pi's own clock (fine with internet)
# Once a source has synced, time carries forward from it on the Pi's monotonic
# clock, which stays accurate for hours even after the GPS loses its fix.

CLOCK_WARNING_SECONDS = 2.0     # log when the Pi's clock is off by more than this


class TimeKeeper:
    SOURCES = ("gps", "laptop", "system")

    def __init__(self):
        self._lock = threading.Lock()
        self._gps_ref = None        # (UTC datetime from GPS, monotonic time it arrived)
        self._laptop_ref = None     # (UTC datetime from the browser, monotonic time it arrived)
        self._warned = set()

    def update_from_gps(self, gps_time: datetime):
        with self._lock:
            first = self._gps_ref is None
            self._gps_ref = (gps_time.astimezone(timezone.utc), time.monotonic())
        if first:
            logger.info("Synced to GPS time")
            self._check_system_clock("gps", gps_time)

    def update_from_laptop(self, epoch_ms: float):
        laptop_time = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
        with self._lock:
            first = self._laptop_ref is None
            self._laptop_ref = (laptop_time, time.monotonic())
        if first:
            logger.info("Received laptop time")
            self._check_system_clock("laptop", laptop_time)

    @property
    def source(self) -> str:
        with self._lock:
            if self._gps_ref is not None:
                return "gps"
            if self._laptop_ref is not None:
                return "laptop"
        return "system"

    def now(self) -> datetime:
        """Current UTC time from the best available source."""
        with self._lock:
            ref = self._gps_ref or self._laptop_ref
        if ref is None:
            return datetime.now(timezone.utc)
        synced_time, synced_at = ref
        return synced_time + timedelta(seconds=time.monotonic() - synced_at)

    def _check_system_clock(self, source: str, true_time: datetime):
        offset = (datetime.now(timezone.utc) - true_time).total_seconds()
        if abs(offset) > CLOCK_WARNING_SECONDS and source not in self._warned:
            self._warned.add(source)
            logger.warning("The Pi's clock is off by %.1f s; using %s time for astronomy.", offset, source)


# One shared instance: the GPS reader and the web app feed it, CelestialObject reads it
time_keeper = TimeKeeper()
