import logging
import threading

import pynmea2
import serial

import config
from TimeKeeper import time_keeper

logger = logging.getLogger("GT-U7 GPS")


class GpsUartReceiver:
    def __init__(self, port: str = config.GPS_PORT, baud: int = config.GPS_BAUD):
        self.port = port
        self.baud = baud
        # Fallback location from .env until the GPS has a fix
        self.lat: float = config.DEFAULT_LATITUDE
        self.lon: float = config.DEFAULT_LONGITUDE
        self.has_fix: bool = False
        self.ser = None
        self.timestamp = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self) -> bool:
        """Open the port and start reading. Returns False (and keeps the
        fallback location) if the GPS isn't connected."""
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
        except serial.SerialException as e:
            logger.warning("Could not open %s (%s). Using the fallback location.", self.port, e)
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Reading NMEA from %s", self.port)
        return True

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self.ser is not None and self.ser.is_open:
            self.ser.close()

    def get_coords(self) -> tuple:
        with self._lock:
            return (self.lat, self.lon)

    def _set_fix(self, has_fix: bool):
        if has_fix != self.has_fix:
            if has_fix:
                logger.info("Established GPS fix")
            else:
                logger.warning("GPS fix lost, waiting for fix...")
        self.has_fix = has_fix

    def _run(self):
        while not self._stop_event.is_set():
            try:
                line = self.ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    msg = pynmea2.parse(line)
                    if msg.status == 'A':
                        with self._lock:
                            self.lat = msg.latitude
                            self.lon = msg.longitude
                            self.timestamp = msg.timestamp
                        if msg.datestamp is not None:
                            time_keeper.update_from_gps(msg.datetime)    # UTC, from the satellites
                        self._set_fix(True)
                    else:
                        self._set_fix(False)
            except pynmea2.ParseError:
                continue
            except serial.SerialException as e:
                # Cable pulled or port gone: report it and retry instead of dying
                logger.error("Serial error: %s. Retrying in 2 s.", e)
                self._set_fix(False)
                self._stop_event.wait(2)
                self._reopen()

    def _reopen(self):
        try:
            if self.ser is not None:
                self.ser.close()
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
        except serial.SerialException:
            pass
