import smbus
import time

bus = smbus.SMBus(1)  # Use defaualt I2C channel 1
PCF8591_ADDR = 0x48  # Change if different from i2cdetect
sensor_channel = 0  # AIN0 is used for soil moisture sensor

def read_light_level(channel):
    bus.write_byte(PCF8591_ADDR, channel)  # Select AIN0 (light sensor)
    raw_value = bus.read_byte(PCF8591_ADDR)  # Read ADC value (0-255)
    invert_value = 255 - raw_value
    return invert_value

while True:
    light_level = read_light_level(sensor_channel)
    print(f"Light Level: {light_level:.2f} ")
    time.sleep(1)