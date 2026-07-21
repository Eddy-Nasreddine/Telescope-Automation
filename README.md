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
- **Manual Jogging** — left, right, up, down buttons for manual fine adjustment; hold to move, release to stop
- **Move To** — enter target azimuth and elevation coordinates to slew to a position
- **Celestial Object Tracking** — select a planet or star and the system automatically moves to it (tracking in real time is still in progress)
- **Star Calibration** — moves to Polaris, allows manual jogging to center the star, then calculates and stores azimuth and elevation error offsets applied to all future moves (in progress) 
- **GPS Integration** — acquires observer coordinates for accurate astrometric calculations
- **Live Camera Feed** — MJPEG stream from an attached camera with adjustable exposure, gain, and brightness
- **System Status** — real-time display of azimuth, elevation, moving state, GPS lock, and MCU connection status

---

## Project Structure

```
Telescope-Automation/
├── app/
│   ├── app.py                  # Flask application and routes
│   ├── TelescopeController.py  # Main control layer
│   ├── MotorController.py      # Stepper motor abstraction
│   ├── CelestialObject.py      # Astrometric coordinate calculations
│   ├── GpsUartReceiver.py      # GPS serial reader
│   ├── CameraStream.py         # MJPEG camera stream
│   └── templates/
│       └── index.html          # Web interface
├── main.c                      # STM32 HAL firmware
└── README.md
```

---

## Notes

- The system initializes at a hardcoded home position (azimuth: 0°, elevation: 90°) on the STM32 side — physically move the telescope to match this position before powering on, or use **Reset Origin** after repositioning
- Maximum steps per command is 4000, equivalent to one full 360° rotation
- Flask runs with `use_reloader=False` to prevent the serial port from being opened twice
