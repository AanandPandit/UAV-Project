# Vision-Based UAVs for Search and Rescue: Enhancing Operations in Disaster Zones

## Project Overview
This project aims to develop an Unmanned Aerial Vehicle (UAV) system equipped with computer vision to enhance search and rescue operations in disaster zones such as landslides, road accidents, and flight crashes. The UAV integrates real-time object detection, autonomous flight control, and data transmission to provide actionable insights for rescue teams.

### Key Features
- **Real-time Object Detection**: Uses YOLOv8 to detect survivors, vehicles, fire, and other critical objects.
- **Autonomous Flight**: PID control algorithm stabilizes the UAV during flight.
- **Data Transmission**: ESP32 CAM module transmits live video feed to a ground station.
- **User Dashboard**: PyQt5-based interface for monitoring and control.

## Hardware Components
- **Frame**: Lightweight structural support.
- **Motors**: 4x DC Brushless Motors for propulsion.
- **ESCs**: 4x Electronic Speed Controllers.
- **Arduino UNO R4**: Flight controller.
- **MPU6050 Sensor**: Gyroscope and accelerometer for stability.
- **ESP32 CAM Module**: 5MP camera for real-time video.
- **Drone Remote/Receiver**: Flysky CT6B for manual control.
- **Battery**: 11.1V Li-Po for power.

## Software Components
- **Flight Control**: PID algorithm for stabilization (Arduino).
- **Object Detection**: YOLOv8 model trained on custom datasets (Python).
- **Communication**: HTTP protocol for video transmission (ESP32 CAM).
- **Dashboard**: PyQt5 interface for real-time monitoring (Python).

## Datasets
1. **COCO (2017)**: General object detection (80 classes).
2. **Emergency Teams**: Detects rescue personnel (boots, gloves, helmet, vest).
3. **Emergency Vehicles/Fire/Smoke**: Detects hazards and vehicles (ambulance, fire, smoke, etc.).


## Installation
1. **Hardware Setup**:
   - Assemble the UAV frame and connect motors, ESCs, Arduino, MPU6050, and ESP32 CAM.
   - Power the system with the 11.1V Li-Po battery.

2. **Software Setup**:
   - Flash `espcam_code.ino` to the ESP32 CAM module.
   - Upload flight control code (`YMFC-AL_*.ino`) to the Arduino UNO R4.
   - Install Python dependencies:
     ```bash
     pip install -r requirements.txt
     ```

3. **Model Training**:
   - Use `train.ipynb` to train YOLOv8 on custom datasets (Dataset2/Dataset3).

## Usage
1. **Pre-flight Checks**:
   - Calibrate ESCs and sensors.
   - Ensure battery and camera are functional.

2. **Operation**:
   - Launch the UAV dashboard:
     ```bash
     python main.py
     ```
   - Manually control the UAV via remote or use autonomous mode.

3. **Output**:
   - Real-time alerts and annotated video feed.
   - Automated reports (PDF, images, videos) saved in `/output`.

## Performance Metrics
- **Object Detection**: 85% accuracy (YOLOv8).
- **Latency**: 300ms for data transmission.
- **Battery Life**: ~25 minutes per charge.

## Limitations
- Limited battery life and payload capacity.
- Dependence on stable wireless connectivity.
- Lower accuracy for fire/smoke detection (~70%).

## Future Work
- Extend battery life and improve camera resolution.
- Enhance autonomous navigation with obstacle avoidance.
- Integrate thermal imaging for low-visibility conditions.

## Contributors
- Aanand Pandit
- Gajjala Sree Hareesh
- Kakarla Kavitha
- Stephens Rajesh


