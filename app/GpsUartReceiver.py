import serial
import pynmea2
import threading

class GpsUartReceiver:
    def __init__(self):
        self.coords: tuple = None
        self.lat: float = 53.62300344381324
        self.lon: float = -113.51295247822964
        self.has_fix: bool = None
        self.ser = None
        self.timestamp = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        
    def start(self):
        self.ser = serial.Serial('/dev/ttyAMA3', 9600, timeout=1)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("<GT-U7 GPS>:: reading NMEA from /dev/ttyAMA3")
        
    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        
    def get_coords(self) -> tuple:
        with self._lock:
            return (self.lat, self.lon)
        
    def _run(self):
        while True:
            try:
                line = self.ser.readline().decode('ascii', errors='replace').strip()
                if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    msg = pynmea2.parse(line)
                    if msg.status == 'A':  
                        print("<GT-U7 GPS>:: Established aGPS fix")
                        self.lat = msg.latitude
                        self.lon = msg.longitude
                        self.timestamp = msg.timestamp
                        self.has_fix = True
                    else:
                        print("<GT-U7 GPS>:: Waiting for GPS fix...")
                        self.has_fix = False
            except pynmea2.ParseError:
                continue
            except KeyboardInterrupt:
                break
        
        
        
    
    