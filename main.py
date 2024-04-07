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
            try:
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
            except UnicodeDecodeError:
                pass

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
            # time.sleep(0.1)

        GPIO.output(motor, GPIO.LOW)

def initialize_position(current_clock_minute):
    current_minute_of_day = int(time.strftime("%H")) * 60 + int(time.strftime("%M"))
    steps = current_minute_of_day - current_clock_minute
    print("Moving " + str(steps) + " steps to initialize the clock to " + str(current_clock_minute) + " minutes")
    move_steps(steps)


def clock_motor_thread():
    while True:
        start_time = time.time()
        move_steps(2)
        end_time = time.time()

        diff = 10 - (end_time - start_time)

        if diff > 0:
            time.sleep(diff)
        else:
            print("Motor took too long to move. Maybe a sensor error?")

if __name__ == '__main__':
    atexit.register(exit_handler)
    threading.Thread(target=serial_thread).start()
    initialize_position(120) # 2 am
    threading.Thread(target=clock_motor_thread).start()
