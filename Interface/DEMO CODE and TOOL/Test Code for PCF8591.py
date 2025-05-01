import smbus
import time

bus = smbus.SMBus(1)
address = 0x48

try:
    # Ttry to read PCF8591
    bus.write_byte(address, 0)
    value = bus.read_byte(address)
    print(f"SUCCESS: {value}")
except Exception as e:
    print(f"ERROR: {e}")