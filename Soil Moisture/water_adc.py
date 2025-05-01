import smbus
import time

# I2C setup
bus = smbus.SMBus(1)  # Use I2C channel 1
pcf8591_address = 0x48  # PCF8591 default I2C address
sensor_channel = 1  # AIN1 is used for soil moisture sensor

# Function to read ADC value
def read_adc(channel):
    bus.write_byte(pcf8591_address, channel)  # Select ADC channel
    value = bus.read_byte(pcf8591_address)  # Read ADC value (0-255)
    return value

# Define moisture level thresholds (adjust based on testing)
DRY_THRESHOLD = 160      # Below this value is Dry
MOIST_THRESHOLD = 140   # Between DRY and MOIST is Moist
# Above MOIST_THRESHOLD is Wet

while True:
    moisture_value = read_adc(sensor_channel)  # Read from PCF8591

    # Determine moisture level
    if moisture_value > DRY_THRESHOLD:
        print("Soil is DRY!")
    elif DRY_THRESHOLD >= moisture_value > MOIST_THRESHOLD:
        print("Soil is MOIST!")
    else:
        print("Soil is WET!")

    print(f"Raw ADC Value: {moisture_value}")  # Debugging purpose
    time.sleep(1)  # Wait before next reading
