

## Features

- **Displays Normal status animation by default** - Normal status animation plays automatically after system startup
- **Touch Screen/Mouse Control** - operate the system by touching the buttons on the screen.
- **Sensors on Demand** - Sensors are read only at the click of a button, saving resources.
- **Status Display** - displays sensor values in normal state and plays corresponding animation in abnormal state
- **Voice Interaction** - support voice quiz function, you can talk to the “plant”.
- **Intelligent Degradation** - automatically enters the simulation mode when the sensor is not available.




1. Clone or download the code to the Raspberry Pi.
2. Install dependencies:
   ```bash
   bash install-dependencies.sh
   ```
3. Make sure the video file path is correct (configured in the `VIDEOS` dictionary in the code)
4. Run the program:
   ```bash
   python3 plant_monitor.py
   ```
   In some cases, superuser privileges may be required:
   ```bash 
   sudo python3 plant_monitor.py
   ```



- **Soil Moisture Sensor**: connected to AIN1 channel of PCF8591
- **Light sensor**: connected to AIN0 channel of PCF8591
- **DHT sensor**: connect to GPIO 4 (can be modified in code)





1. **Water** - Click on this button to read the soil moisture sensor
2. **Light** - Click this button to read the light sensor
3. **DHT** - click this button to read the temperature and humidity sensor
4. **Voice** - Click on this button to enable/disable voice interaction.

When the sensor reading is normal, the system will display the value in the top right panel. When the sensor reading is abnormal (e.g. soil is too dry), the system will play an animation of the corresponding abnormal state and will automatically return to the normal state after 5 seconds.

## Voice Interaction

With the voice function turned on, you can have a simple voice interaction with the system:

- “How is the soil moisture?” - The system will read and broadcast the soil moisture status.
- “How's the light?” - The system will read and announce the light status.
- “What is the temperature?” - The system reads and reports the current temperature.
- “What's the air humidity?” - The system reads and displays the air humidity.

## Configuration and Customization

The following configurations can be modified in the code:

- **SENSOR THRESHOLDS**: modify the `SENSOR_THRESHOLDS` dictionary to adjust the thresholds of each sensor
- **VIDEO PATH**: modify the path in the `VIDEOS` dictionary to use your own video
- **Screen size**: modify the `SCREEN_WIDTH` and `SCREEN_HEIGHT` variables to accommodate different screens
- **DHT sensor type**: modify the `sensor_type` parameter (11 for DHT11, 22 for DHT22) when initializing the `DHTSensor` class

## Analog mode

When running in a non-Raspberry Pi environment or when certain hardware is not available, the system will automatically enter analog mode:

- Analog sensor data will be generated
- Video playback will be skipped, but the status will still be updated.
- Speech recognition will use a preset list of questions

This allows you to test the logic of the system in a development environment without having to connect actual hardware.



## Development Information

This system uses the following technologies:

- Python 3
- Pygame (user interface)
- RPi.GPIO (GPIO control)
- smbus (I2C communication)
- SpeechRecognition (speech recognition)
- gTTS (text-to-speech conversion)
- MPV (video playback)

## System architecture diagram

``
Hardware layer.
  - Display/Touch Screen
  - ADC Converter + Soil Moisture/Light Sensor
  - DHT temperature and humidity sensor
  - Microphone/Speaker

Software Layer: User Interface / Touch Buttons
  - User Interface / Touch Buttons
  - Video Playback Module
  - Sensor Reading Module
  - Speech Recognition/Synthesis Module
  - Business Logic Processing
``