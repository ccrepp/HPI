#!/usr/bin/env python3
"""
Smart Plant Monitoring System - Raspberry Pi 5 Compatible Version
- On-demand sensor reading via touch/mouse interface
- Default "Normal" state animation
- Display sensor values when state is normal
- Show corresponding animation when state is abnormal
- Adapted for Raspberry Pi 5, using PCF8591 ADC for light sensor reading

Modified from XIASIZHE 20476377 original code
"""

import os
import time
import threading
import subprocess
import smbus
import json
import pygame
from pygame.locals import *
import numpy as np

# Allow simulation mode when not running on Raspberry Pi
try:
    import RPi.GPIO as GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    print("Warning: GPIO library not available, running in simulation mode")
    GPIO_AVAILABLE = False

# I2C configuration (for soil moisture and light sensors)
I2C_ADDRESS = 0x48  # PCF8591 default I2C address
try:
    bus = smbus.SMBus(1)  # Use I2C-1
    # Try to read once to confirm I2C bus is working
    try:
        bus.write_byte(I2C_ADDRESS, 0)
        bus.read_byte(I2C_ADDRESS)
        I2C_AVAILABLE = True
    except:
        print("Warning: PCF8591 not available on I2C bus, using simulation mode for ADC sensors")
        I2C_AVAILABLE = False
except:
    print("Warning: I2C bus not available, running in simulation mode")
    I2C_AVAILABLE = False

# Video paths
VIDEOS = {
    "normal": "/home/UNM.RPI4B/videos/normal.mp4",    # Default state
    "dry": "/home/UNM.RPI4B/videos/dry.mp4",          # Dry soil state
    "wet": "/home/UNM.RPI4B/videos/wet.mp4",          # Wet soil state
    "dark": "/home/UNM.RPI4B/videos/dark.mp4",        # Low light state
    "bright": "/home/UNM.RPI4B/videos/bright.mp4",    # Bright light state
    "hot": "/home/UNM.RPI4B/videos/hot.mp4",          # High temperature state
    "cold": "/home/UNM.RPI4B/videos/cold.mp4",        # Low temperature state
    "humid": "/home/UNM.RPI4B/videos/humid.mp4"       # High humidity state
}

# Sensor threshold configuration
SENSOR_THRESHOLDS = {
    "moisture": {
        "dry": 160,    # Above this value is dry
        "wet": 140     # Below this value is wet
    },
    "light": {
        "dark": 80,    # Below this value is dark
        "bright": 200  # Above this value is bright
    },
    "temperature": {
        "cold": 15,    # Below this value is cold
        "hot": 30      # Above this value is hot
    },
    "humidity": {
        "dry_air": 30, # Below this value is dry air
        "humid": 70    # Above this value is humid
    }
}

# Sensor pin configuration
PIN_CONFIG = {
    "dht": 4          # DHT sensor pin
}

# Global variables
current_video = "normal"
video_process = None
is_displaying_values = False
sensor_values = {
    "moisture": 0,
    "light": 0,
    "temperature": 0,
    "humidity": 0
}
sensor_status = {
    "moisture": "normal",
    "light": "normal",
    "temperature": "normal",
    "humidity": "normal"
}
lock = threading.Lock()

# Initialize pygame (for screen display and button handling)
pygame.init()
pygame.mixer.init()
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
# Adapt to screen size or use window mode if not on Raspberry Pi
if 'DISPLAY' in os.environ and ':0' in os.environ['DISPLAY']:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
else:
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Plant Monitoring System")
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# MPV player path
MPV_PATH = "/usr/bin/mpv"

class DHTSensor:
    """DHT temperature and humidity sensor class"""
    def __init__(self, pin=PIN_CONFIG["dht"], sensor_type=22):
        self.pin = pin
        self.sensor_type = sensor_type  # 11 for DHT11, 22 for DHT22

    def read(self):
        """Read DHT sensor data"""
        try:
            # Use the existing dht_test.py script to read temperature and humidity
            output = subprocess.check_output(
                ["python3", "dht_test.py", str(self.sensor_type), str(self.pin)],
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            # Parse output
            if "Temp:" in output and "Humidity:" in output:
                parts = output.split()
                temp_index = parts.index("Temp:")
                humidity_index = parts.index("Humidity:")
                
                temperature = float(parts[temp_index + 1])
                humidity = float(parts[humidity_index + 1])
                
                return temperature, humidity
            else:
                print(f"DHT read error output: {output}")
                return None, None
        except Exception as e:
            print(f"DHT read error: {e}")
            return None, None

def read_adc(channel):
    """Read ADC value from PCF8591, return simulated value if unavailable"""
    if I2C_AVAILABLE:
        try:
            bus.write_byte(I2C_ADDRESS, channel)
            # First read to initialize
            bus.read_byte(I2C_ADDRESS)  
            # Second read to get actual value
            value = bus.read_byte(I2C_ADDRESS)
            return value
        except Exception as e:
            print(f"ADC read error: {e}")
            return simulate_adc_value(channel)
    else:
        return simulate_adc_value(channel)

def simulate_adc_value(channel):
    """Generate simulated ADC values when actual sensors are unavailable"""
    import random
    if channel == 0:  # Light sensor
        return random.randint(80, 200)
    elif channel == 1:  # Soil moisture sensor
        return random.randint(130, 170)
    return random.randint(100, 200)

def read_moisture():
    """Read soil moisture sensor"""
    value = read_adc(1)  # AIN1 channel
    with lock:
        sensor_values["moisture"] = value
        
        # Determine moisture status
        if value > SENSOR_THRESHOLDS["moisture"]["dry"]:
            sensor_status["moisture"] = "dry"
        elif value < SENSOR_THRESHOLDS["moisture"]["wet"]:
            sensor_status["moisture"] = "wet"
        else:
            sensor_status["moisture"] = "normal"
    
    return value, sensor_status["moisture"]

def read_light():
    """Read light sensor - PCF8591 ADC mode only"""
    # Try to read ADC value
    adc_value = None
    
    if I2C_AVAILABLE:
        try:
            # Try multiple reads to avoid occasional errors
            for _ in range(3):
                adc_value = read_adc(0)  # AIN0 channel
                if adc_value is not None:
                    break
                time.sleep(0.1)
        except Exception as e:
            print(f"Light sensor read error: {e}")
            adc_value = None
    
    # If ADC read fails, use simulated value
    if adc_value is None:
        adc_value = simulate_adc_value(0)
        print(f"Using simulated light value: {adc_value}")
    
    with lock:
        sensor_values["light"] = adc_value
        
        # Determine light status
        if adc_value < SENSOR_THRESHOLDS["light"]["dark"]:
            sensor_status["light"] = "dark"
        elif adc_value > SENSOR_THRESHOLDS["light"]["bright"]:
            sensor_status["light"] = "bright"
        else:
            sensor_status["light"] = "normal"
    
    return adc_value, sensor_status["light"]

def read_dht():
    """Read DHT temperature and humidity sensor"""
    if GPIO_AVAILABLE:
        dht = DHTSensor()
        temperature, humidity = dht.read()
    else:
        # Simulation mode, return reasonable simulated values
        import random
        temperature = random.uniform(15, 30)
        humidity = random.uniform(30, 70)
    
    if temperature is not None and humidity is not None:
        with lock:
            sensor_values["temperature"] = temperature
            sensor_values["humidity"] = humidity
            
            # Determine temperature status
            if temperature < SENSOR_THRESHOLDS["temperature"]["cold"]:
                sensor_status["temperature"] = "cold"
            elif temperature > SENSOR_THRESHOLDS["temperature"]["hot"]:
                sensor_status["temperature"] = "hot"
            else:
                sensor_status["temperature"] = "normal"
                
            # Determine humidity status
            if humidity < SENSOR_THRESHOLDS["humidity"]["dry_air"]:
                sensor_status["humidity"] = "dry_air"
            elif humidity > SENSOR_THRESHOLDS["humidity"]["humid"]:
                sensor_status["humidity"] = "humid"
            else:
                sensor_status["humidity"] = "normal"
    
    return (temperature, humidity, 
            sensor_status["temperature"], 
            sensor_status["humidity"])

def play_video(video_key, duration=None):
    """Play the specified video in the upper 70% of the screen"""
    global video_process, current_video
    
    # Update current video state
    current_video = video_key
    
    # Create a black transition screen
    transition_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    transition_surface.fill((0, 0, 0))
    
    # Display transition screen
    screen.blit(transition_surface, (0, 0))
    
    # Add text indicator
    text = font.render(f"Loading {video_key.upper()} state...", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - text.get_height()//2))
    
    pygame.display.flip()
    
    # If a video process is running, terminate it
    if video_process and video_process.poll() is None:
        video_process.terminate()
        try:
            video_process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            video_process.kill()
    
    # Short delay for transition
    time.sleep(0.3)
    
    # Check if the video file exists
    video_path = VIDEOS.get(video_key)
    if not video_path or not os.path.exists(video_path):
        print(f"Warning: Video file does not exist - {video_path}")
        return
    
    # Calculate video area (top 70% of screen)
    video_height = int(SCREEN_HEIGHT * 0.7)  # 70% of screen height
    
    # Build MPV command with specific geometry
    cmd = [
        MPV_PATH,
        "--loop" if duration is None else "--no-loop",
        # "--fs",  # Remove fullscreen
        f"--geometry=1024x{video_height}+0+0",  # Set size and position (width x height + x + y)
        "--no-border",  # Remove window decorations
        "--ontop",      # Keep video on top
        "--no-input-terminal",
        "--really-quiet",
        "--no-osc",
        video_path
    ]
    
    # Set environment variables
    my_env = os.environ.copy()
    my_env["DISPLAY"] = ":0"
    
    try:
        video_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=my_env
        )
        
        # If duration is specified, restore normal video after that time
        if duration:
            def restore_normal():
                time.sleep(duration)
                play_video("normal")
            
            threading.Thread(target=restore_normal, daemon=True).start()
            
    except Exception as e:
        print(f"Error playing video: {e}")

def display_osd_value(sensor_type, value, status="normal"):
    """Display sensor value on screen"""
    global is_displaying_values
    
    # Set OSD message
    osd_message = ""
    if sensor_type == "water":
        osd_message = f"Soil Moisture: {value} - {status.upper()}"
    elif sensor_type == "light":
        osd_message = f"Light Level: {value} - {status.upper()}"
    elif sensor_type == "temperature":
        osd_message = f"Temperature: {value}°C - {status.upper()}"
    elif sensor_type == "humidity":
        osd_message = f"Air Humidity: {value}% - {status.upper()}"
    
    print(f"Display OSD: {osd_message}")
    
    # Only show abnormal state videos when status is not normal
    if status != "normal" and sensor_type in ["water", "light", "temperature", "humidity"]:
        video_key = {
            "water": {"dry": "dry", "wet": "wet"},
            "light": {"dark": "dark", "bright": "bright"},
            "temperature": {"hot": "hot", "cold": "cold"},
            "humidity": {"humid": "humid", "dry_air": "normal"}
        }
        
        status_video = video_key.get(sensor_type, {}).get(status)
        if status_video:
            play_video(status_video, duration=5)  # Play for 5 seconds then restore normal
    
    # Set display flag
    is_displaying_values = True
    
    # Start a thread to clear the display
    def clear_osd():
        time.sleep(5)  # Display for 5 seconds
        global is_displaying_values
        is_displaying_values = False
    
    threading.Thread(target=clear_osd, daemon=True).start()

def draw_ui(buttons, button_states):
    """Draw the user interface"""
    # Draw background
    screen.fill((0, 0, 0))
    
    # Draw clickable buttons
    for btn in buttons:
        # If button is pressed, use green fill
        is_pressed = button_states.get(btn["action"], False)
        
        # Select color based on button state
        if is_pressed:
            color = (100, 255, 100)  # Bright green when pressed
            text_color = (0, 0, 0)
            border = 0
        else:
            color = (80, 80, 80)  # Gray when not pressed
            text_color = (255, 255, 255)
            border = 2
        
        # Draw button
        pygame.draw.rect(screen, color, btn["rect"], border)
        text = font.render(btn["text"], True, text_color)
        text_x = btn["rect"].x + (btn["rect"].width - text.get_width()) // 2
        text_y = btn["rect"].y + (btn["rect"].height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))
    
    # Draw current video status at the top
    status_text = f"Current State: {current_video.upper()}"
    status = font.render(status_text, True, (255, 255, 255))
    screen.blit(status, (20, 20))
    
    # Display current sensor values
    if is_displaying_values:
        with lock:
            text_lines = [
                f"Moisture: {sensor_values['moisture']} ({sensor_status['moisture']})",
                f"Light: {sensor_values['light']} ({sensor_status['light']})",
                f"Temperature: {sensor_values['temperature']:.1f}°C ({sensor_status['temperature']})",
                f"Humidity: {sensor_values['humidity']:.1f}% ({sensor_status['humidity']})"
            ]
        
        # Display sensor data panel in top right
        panel_width = 300
        panel_height = 150
        panel_x = SCREEN_WIDTH - panel_width - 20
        panel_y = 20
        
        # Draw semi-transparent panel background
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 180))  # Black semi-transparent background
        screen.blit(panel_surface, (panel_x, panel_y))
        
        # Add title
        title_text = "Sensor Data"
        title = small_font.render(title_text, True, (255, 255, 255))
        screen.blit(title, (panel_x + 10, panel_y + 10))
        
        # Add data lines
        for i, line in enumerate(text_lines):
            color = (255, 255, 255)  # Default white
            # Color based on status
            if "normal" not in line:
                color = (255, 100, 100)  # Red for abnormal status
                
            text = small_font.render(line, True, color)
            screen.blit(text, (panel_x + 10, panel_y + 40 + i * 25))
    
    pygame.display.flip()

def check_mpv_path():
    """Check if mpv exists and return the correct path"""
    global MPV_PATH
    
    # First check default path
    if os.path.exists(MPV_PATH):
        print(f"Found mpv: {MPV_PATH}")
        return True
    
    # Try to find mpv using which command
    try:
        result = subprocess.run(["which", "mpv"], stdout=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stdout.strip():
            MPV_PATH = result.stdout.strip()
            print(f"Found mpv: {MPV_PATH}")
            return True
    except:
        pass
    
    # Try other possible locations
    alt_paths = [
        "/bin/mpv",
        "/usr/local/bin/mpv",
        "/usr/bin/mpv"
    ]
    
    for path in alt_paths:
        if os.path.exists(path):
            MPV_PATH = path
            print(f"Found mpv: {MPV_PATH}")
            return True
    
    print("Warning: Could not find mpv player")
    return False

def main():
    """Main function"""
    print("Smart Plant Monitoring System for Raspberry Pi 5 starting...")
    
    # Check MPV path
    check_mpv_path()
    
    # Check video files
    missing_videos = []
    for key, path in VIDEOS.items():
        if not os.path.exists(path):
            missing_videos.append(f"{key}: {path}")
    
    if missing_videos:
        print("Warning: The following video files do not exist:")
        for v in missing_videos:
            print(f"  - {v}")
        
        # Allow modifying video paths
        valid_input = False
        while not valid_input:
            choice = input("Modify video paths (m), continue (c), or quit (q)? ").lower()
            if choice == "m":
                valid_input = True
                base_path = input("Enter the base path for video files: ")
                for key in VIDEOS:
                    VIDEOS[key] = os.path.join(base_path, f"{key}.mp4")
            elif choice == "c":
                valid_input = True
                # Continue with current paths
                pass
            elif choice == "q":
                return
    
    # Double-check modified video paths
    missing_after_modify = []
    for key, path in VIDEOS.items():
        if not os.path.exists(path):
            missing_after_modify.append(path)
    
    if missing_after_modify:
        print("Warning: The following video files still do not exist:")
        for path in missing_after_modify:
            print(f"  - {path}")
        
        choice = input("Continue anyway? (y/n): ").lower()
        if choice != 'y':
            return
    
    # Play default video (if available)
    if os.path.exists(VIDEOS["normal"]):
        play_video("normal")
    
    # Create button definitions
    buttons = [
        {"text": "Moisture", "rect": pygame.Rect(50, SCREEN_HEIGHT - 60, 160, 50), "action": "water"},
        {"text": "Light", "rect": pygame.Rect(230, SCREEN_HEIGHT - 60, 160, 50), "action": "light"},
        {"text": "Temp/Humid", "rect": pygame.Rect(410, SCREEN_HEIGHT - 60, 160, 50), "action": "dht"},
        {"text": "Reset", "rect": pygame.Rect(590, SCREEN_HEIGHT - 60, 160, 50), "action": "reset"}
    ]
    
    # Button states
    button_states = {button["action"]: False for button in buttons}
    
    # Main loop
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    running = False
                elif event.type == MOUSEBUTTONDOWN:
                    # Check if click is on a button
                    pos = pygame.mouse.get_pos()
                    for button in buttons:
                        if button["rect"].collidepoint(pos):
                            # Set button state to pressed
                            button_states[button["action"]] = True
                            
                            # Perform corresponding action
                            if button["action"] == "water":
                                moisture, status = read_moisture()
                                display_osd_value("water", moisture, status)
                            elif button["action"] == "light":
                                light, status = read_light()
                                display_osd_value("light", light, status)
                            elif button["action"] == "dht":
                                temp, humid, temp_status, humid_status = read_dht()
                                if temp is not None and humid is not None:
                                    display_osd_value("temperature", temp, temp_status)
                                    # Show humidity after 2 seconds
                                    threading.Timer(2, lambda: display_osd_value("humidity", humid, humid_status)).start()
                            elif button["action"] == "reset":
                                # Return to normal state
                                play_video("normal")
                            
                            # Restore button state after 0.2 seconds
                            def reset_button(action):
                                time.sleep(0.2)
                                button_states[action] = False
                            
                            threading.Thread(target=reset_button, args=(button["action"],), daemon=True).start()
            
            # Draw UI
            draw_ui(buttons, button_states)
            
            # Limit frame rate
            clock.tick(30)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        # Clean up resources
        if video_process and video_process.poll() is None:
            video_process.terminate()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        pygame.quit()
        print("Program closed")

if __name__ == "__main__":
    import sys
    main()