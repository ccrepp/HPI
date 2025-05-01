import smbus
import time

# I2C Address of ADC
I2C_ADDRESS = 0x48  #default address

# initialise I2C bus (1 for RPI4/5)
bus = smbus.SMBus(1)

# calibration variables
SENSOR_MAX = 0
SENSOR_MIN = 255            # 8-bit ADC max value
CALIBRATION_READINGS = 100  # number of calibration samples

''' read_adc function to read from convertor '''
def read_adc(channel):
    
    # testing for possible connection errors
    if channel <0 or channel > 3:
        raise ValueError("PCF8591 has ONLY 4 Input Channels (0-3)")
    
    bus.write_byte(I2C_ADDRESS, 0x40 | channel)     # channel selection (AIN0-AIN3)
    bus.read_byte(I2C_ADDRESS)                      # dummy read to initialise ADC
    value = bus.read_byte(I2C_ADDRESS)              # actual ADC read
    
    return value

''' Calibration Process '''
print("=============")
print("Calibrating Sensor... Please ensure the soil is both dry and wet during this process.")
print("=============\n\n")

for i in range(CALIBRATION_READINGS):
    value = read_adc(1)
    
    if value > SENSOR_MAX:
        SENSOR_MAX = value

    if value < SENSOR_MIN:
        SENSOR_MIN = value

    print(f"Reading {i+1}: {value} (Min: {SENSOR_MIN}, Max: {SENSOR_MAX})")
    time.sleep(0.2)

print("\n-------------------")
print(f"Calibration Complete!\nMIN: {SENSOR_MIN} (Wet)\nMAX: {SENSOR_MAX} (Dry)")
print("-------------------\n")
time.sleep(5)

try:
    while True:
        moisture_value = read_adc(1)
        percent = round( ( (SENSOR_MAX - moisture_value) / (SENSOR_MAX - SENSOR_MIN) ) * 100)
        print(f"Current Moisture Level: {moisture_value}/{SENSOR_MAX} ({percent}% Moisture)")
        
        if percent >= 70:
            print("SOIL IS WET >>:3")
        elif percent >= 40:
            print("SOIL IS MOIST :DD")
        else:
            print("SOIL IS DRY ;-;")
            
        time.sleep(3)

except KeyboardInterrupt:
    print("Exiting...")
    bus.close()
    