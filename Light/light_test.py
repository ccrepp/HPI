import RPi.GPIO as GPIO
import time

# GPIO pin definition
channel = 21

# setting up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(channel, GPIO.IN)

# callback function to test sensor
def callback(channel):
    if GPIO.input(channel):
        print("LOW LIGHT DETECTED >:c")
        print(GPIO.input(channel))
    else :
        print("MUCH LIGHT DETECTED :DD")
        print(GPIO.input(channel))

# setting up GPIO event detection        
GPIO.add_event_detect(channel, GPIO.BOTH, bouncetime=500)
GPIO.add_event_callback(channel, callback)

while True:
    time.sleep(3)