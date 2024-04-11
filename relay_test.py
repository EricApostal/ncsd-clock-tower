import RPi.GPIO as GPIO
import time, serial, threading

photo_sensor = 16

GPIO.setmode(GPIO.BOARD)

GPIO.setup(photo_sensor, GPIO.IN)

def read_photo_sensor():
    while True:
        print(GPIO.input(photo_sensor))
        time.sleep(1)

# read_photo_sensor()

for i in range(5):
    GPIO.setup(37, GPIO.OUT)
    GPIO.output(37, GPIO.HIGH)
    time.sleep(1)

print("done!")
GPIO.cleanup()