# HPI
COMP2019 - SEGP - Group 11 - Human-Plant Interaction

# Table of Contents

- [Prerequisites](#Prerequisites)
  - [Sensors](#Troubleshooting)
  - [Interface](#Interface)
  - [Chatbot](#Chatbot)


## Prerequisites
The following details the dependencies that may be required to run the software

 ### Sensors
- RPI.GPIO (Should be pre-installed, but you can make sure by running:)
  ```
    sudo apt update
    sudo apt install python3-rpi.gpio
  ```
- smbus ( Make sure I²C is enabled via ``` sudo raspi-config ```)
  ```
  sudo apt install python3-smbus
  ```
 ### Interface 
 Use ```pip install ```
- pygame
- OpenCV
- gTTS
- numpy

### Chatbot
- llama-cpp-python (Explained)
- For ai_chat instructions, [Click here](https://github.com/ccrepp/HPI/blob/main/ai_chat/README.md)
