# Autonomous Telescope Control System

A fully automated telescope control system built from scratch across mechanical, electrical, firmware, and software layers. The system is capable of tracking celestial objects in real time using astrometric coordinate calculations, GPS positioning, and precision stepper motor control.

---

## Overview

This project automates the movement and tracking of a telescope mount using two stepper motors — one for azimuth and one for elevation. A Raspberry Pi runs a Flask web application that serves as the user interface, while an STM32L432KC microcontroller handles all low-level motor control over a custom UART protocol. All mechanical components were designed in Onshape and 3D printed, and a custom PCB was designed in KiCad to interface all components cleanly.

---

## Hardware

- **Microcontroller:** STM32L432KC (Nucleo-L432KC)
- **Single Board Computer:** Raspberry Pi
- **Motors:** NEMA 17 (elevation) and NEMA 23 (azimuth) stepper motors
- **GPS Module:** UART-based GPS receiver for real-time observer coordinates
- **PCB:** Custom KiCad design interfacing the Raspberry Pi, STM32, GPS module, and stepper motor drivers
- **Mechanical:** All mounts, brackets, and gear housings designed in Onshape and 3D printed
  - Elevation gear ratio: 12 driver / 120 driven
  - Azimuth gear ratio: 30 driver / 200 driven

---

## Software Stack

| Layer | Technology |
|---|---|
| Web Interface | Flask, HTML, CSS, JavaScript |
| Control Layer | Python |
| Firmware | C (STM32 HAL) |
| Astrometry | Skyfield |
| GPS | UART serial receiver |
| Camera | OpenCV (live MJPEG stream) |

---

## UART Communication Protocol

The Raspberry Pi and STM32 communicate over UART at **115200 baud**. Commands are sent as ASCII strings terminated with `\n`.

### Command Format

| Command | Format | Example | Description |
|---|---|---|---|
| Move | `<az_dir><az_steps><el_dir><el_steps>` | `+0074-0111` | Move azimuth and elevation |
| Stop | `S` | `S` | Stop all motion immediately |
| Handshake | `R` | `R` | Request system state and reset GPIO |
| Set Speed | `T<delay>` | `T50` | Set pulse delay in ms (10–100) |
| Reset Origin | `O` | `O` | Reset azimuth and elevation to home position |

### Response Format

| Response | Example | Description |
|---|---|---|
| `A<float>` | `A90.135` | Current azimuth in degrees |
| `E<float>` | `E45.270` | Current elevation in degrees |
| `T<int>` | `T50` | Current pulse delay |
| `R` | `R` | Handshake acknowledged |
| `D` | `D` | Move completed |
| `S` | `S` | Motion stopped |
| `O` | `O` | Origin reset acknowledged |

---

## Motor Control

- Steps are calculated on the Python side using gear ratio compensation and microstepping
- Azimuth uses **shortest-path logic** — the system always takes the shortest angular route, reducing maximum motor travel by up to 50%
- Azimuth is constrained to 0–360° with automatic wrapping on both the STM32 and Python sides
- Pulse delay is configurable between 10ms and 100ms to control motor speed
- Each motor has a dedicated pulse pin and direction pin

---

## Features

- **Live Web Interface** — control the telescope from any device on the same network via browser
- **Manual Jogging** — left, right, up, down buttons for manual fine adjustment; hold to move, release to stop. A heartbeat from the browser acts as a dead-man switch: if it stops (Wi-Fi drop, laptop asleep), the Pi stops the mount
- **Move To** — enter target azimuth and elevation coordinates to slew to a position
- **Celestial Object Tracking** — select a planet or star and the system moves to it, then re-points every few seconds to follow it until stopped or it drops below the minimum elevation
- **Star Calibration** — moves to Polaris, allows manual jogging to center the star, then calculates and stores azimuth and elevation error offsets applied to all future moves
- **Layered Safety** — every move is checked against elevation limits (0–90°) and a cable-wrap limit (±180° of azimuth from home) in both the API and the controller; moves claim the busy flag atomically; stops are confirmed by the MCU and resent if lost; the MCU link is health-checked while idle
- **GPS Integration** — acquires observer coordinates for accurate astrometric calculations
- **Live Camera Feed** — MJPEG stream from an attached camera with adjustable exposure, gain, and brightness
- **System Status** — real-time display of azimuth, elevation, moving state, GPS lock, and MCU connection status
- **Sky View** — top-down alt/az map showing where the telescope points and where each planet currently sits
- **Event Log** — timestamped console of commands, arrivals, link changes, and errors
- **Night Vision Mode** — all-red theme (including the camera feed) to preserve dark adaptation; toggle with `N`
- **Keyboard Shortcuts** — hold arrow keys to jog, `Esc` to stop all motion

---

## Project Structure

```
Telescope-Automation/
├── app/
│   ├── app.py                  # Flask application and routes
│   ├── config.py               # All settings: ports, gearing, limits, timeouts
│   ├── TelescopeController.py  # Main control layer
│   ├── MotorController.py      # Stepper motor abstraction
│   ├── CelestialObject.py      # Astrometric coordinate calculations
│   ├── GpsUartReceiver.py      # GPS serial reader
│   ├── CameraStream.py         # MJPEG camera stream
│   ├── SimulatedSerial.py      # Fake STM32 for running without the hardware
│   ├── templates/
│   │   └── index.html          # Web interface markup
│   └── static/
│       ├── css/
│       │   ├── base/           # Theme tokens, reset, layout grid, shared components
│       │   └── panels/         # One stylesheet per dashboard panel
│       ├── js/
│       │   ├── main.js         # Front-end entry point (ES modules)
│       │   ├── config.js       # Shared constants (poll rates, 25° minimum elevation)
│       │   ├── state.js        # Shared UI state
│       │   ├── core/           # Status polling, API calls, mode, theme, keyboard shortcuts
│       │   ├── panels/         # One module per dashboard panel
│       │   └── utils/          # DOM, formatting and geometry helpers
│       └── images/             # Planet images
├── data/                       # Ephemeris (de421.bsp) and Hipparcos star catalogue
├── main.c                      # STM32 HAL firmware
├── requirements.txt            # Python dependencies
├── .env.example                # Template for private settings (.env is git-ignored)
└── README.md
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your fallback latitude/longitude
python app/app.py
```

Settings shared by the whole project live in `app/config.py`. Private values (your location) live in `.env`, which git ignores.

**Without the hardware:** set `SIMULATE_HARDWARE=true` in `.env` (or the environment) and the app runs against `SimulatedSerial`, a stand-in that speaks the same UART protocol as `main.c`. Set `PORT` to serve on a port other than 5000.

---

## Notes

- The system initializes at a hardcoded home position (azimuth: 0°, elevation: 90°) on the STM32 side — physically move the telescope to match this position before powering on, or use **Reset Origin** after repositioning
- Maximum steps per command is 4000, equivalent to one full 360° rotation
- Flask runs with `use_reloader=False` to prevent the serial port from being opened twice
