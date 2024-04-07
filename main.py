import RPi.GPIO as GPIO
import time, serial, threading, atexit

ser = serial.Serial('/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_85734323430351600190-if00', 9600, timeout=1)
ser.reset_input_buffer()

# The light value that will signal a change in state
light_threshold = 300

current_state = None

"""
Listens for raw analog light resistance values from the Arduino
"""
def serial_thread():
    global current_state

    while True:
        if ser.in_waiting > 0:
            light_reading = ser.readline().decode('utf-8').rstrip()
            if (light_reading.isalnum()):
                new_state = int(light_reading) < light_threshold
                if (current_state == None):
                    current_state = new_state
                    print("Initial light state: " + str(new_state))
                    continue

                if new_state != current_state:
                    print("Light state changed to: " + str(new_state))
                    current_state = new_state

def exit_handler():
    print("Cleaning up...")
    GPIO.cleanup()

def move_steps(steps: int):
    motor = 11

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(motor, GPIO.OUT)
    for _ in range(steps):
        last_state = current_state
        while (current_state == last_state):
            GPIO.output(motor, GPIO.HIGH)
            time.sleep(0.1)

        GPIO.output(motor, GPIO.LOW)

def clock_motor_thread():
    while True:
        start_time = time.time()
        move_steps(2)
        end_time = time.time()
        
        time.sleep(60 - (end_time - start_time))

if __name__ == '__main__':
    atexit.register(exit_handler)
    threading.Thread(target=serial_thread).start()
    threading.Thread(target=clock_motor_thread).start()
