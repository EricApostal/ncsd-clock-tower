import RPi.GPIO as GPIO
import time, serial, threading, atexit
import sys

ser = serial.Serial('/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_85734323430351600190-if00', 9600, timeout=1)
ser.reset_input_buffer()

# The light value that will signal a change in state
light_threshold = 300
current_step = 0

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
                        # print("Initial light state: " + str(new_state))
                        continue

                    if new_state != current_state:
                        # print("Light state changed to: " + str(new_state))
                        current_state = new_state
            except UnicodeDecodeError:
                pass

def exit_handler():
    print("Cleaning up...")
    GPIO.cleanup()

def init_last_state_file():
    try:
        with open("/home/pi/Documents/last_state.txt", "r") as f:
            print("Last state file already exists")
            return
    except FileNotFoundError:
        with open("/home/pi/Documents/last_state.txt", "w") as f:
            print("Last state file created")
            f.write("0")

def write_last_state(state: int):
    with open("/home/pi/Documents/last_state.txt", "w") as f:
        f.write(str(state))

def read_last_state():
    with open("/home/pi/Documents/last_state.txt", "r") as f:
        return int(f.read())

"""
Move the motor a certain number of steps
Each step represents 30 seconds
"""
def move_steps(steps: int):
    global current_step

    motor = 11

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(motor, GPIO.OUT)
    for _ in range(int(steps)):
        last_state = current_state
        while (current_state == last_state):
            GPIO.output(motor, GPIO.HIGH)
        current_step += 1

        # 720 is the number of steps in 12 hours
        # Once we reach 720, we're back at 12:00
        if (current_step == 720):
            current_step = 0
        write_last_state(current_state)

        GPIO.output(motor, GPIO.LOW)

def _sanitize_minute(minute: int):
    if (minute >= 720):
        minute -= 720
    return minute

def _calculate_steps(current_minute: int, target_minute: int):
    steps = (target_minute - current_minute) * 2
    if (steps < 0):
        steps = 720 + steps
    return steps

def _set_current_step(step: int):
    global current_step
    current_step = step
    if (current_step >= 720):
        current_step = current_step - 720

def initialize_position():
    global current_step

    print("""
    What time does the clock currently display? Do not include AM/PM units.
    Ex: 9:32
    """)
    current_minute_of_day = _sanitize_minute(int(time.strftime("%H")) * 60 + int(time.strftime("%M")))

    # If the current time is past noon, subtract 720 minutes to get the time in the morning
    # This prevents us from forcing the clock to make two rotations
    if (current_minute_of_day > 720):
        current_minute_of_day -= 720

    current_clock_minute = str(input("[USER]: "))
    current_clock_minute = _sanitize_minute(int(current_clock_minute.split(":")[0]) * 60 + int(current_clock_minute.split(":")[1]))
    # print("Current clock minute: " + str(current_clock_minute))
    _set_current_step(current_clock_minute * 2)

   #  print("Current step: " + str(current_step))
    
    steps_to_move = _calculate_steps(current_step/2, current_minute_of_day)
    print("Steps to move: " + str(steps_to_move))
    # print("Current clock minute: " + str(current_step/2))
    # print("Target clock minute: " + str(current_clock_minute))

    # while current_step != current_clock_minute * 2:
    target_steps = 2

    while int(target_steps) > 1:
        target_steps = _calculate_steps(current_step / 2, current_minute_of_day)
        print("The clock is not displaying the correct time, moving " + str(target_steps) + " steps to correct it")
        move_steps(target_steps)

    print("Clock has been calibrated to " + str(current_clock_minute) + " minutes")

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

"""
last_state represents the last step
find the step we are on, and move the motor to that step
"""
def boot_recalibrate():
    global current_step

    last_state = read_last_state()
    current_minute_of_day = int(time.strftime("%H")) * 60 + int(time.strftime("%M"))
    current_step = current_minute_of_day * 2
    step_count = _calculate_steps(last_state, current_step)
    print("Recalibrating to step: " + str(current_step))
    move_steps(step_count)

if __name__ == '__main__':
    if (len(sys.argv) > 2):
        ValueError("Usage: python3 main.py -c (pass -c if you want to callibrate, otherwise leave blank)")

    atexit.register(exit_handler)
    # init_last_state_file()
    threading.Thread(target=serial_thread).start()
    time.sleep(1)

    if (len(sys.argv) == 2 and sys.argv[1] == "-c"):
        print("Calibrating...")
        initialize_position()
    else:
        print("Starting clock...")
        boot_recalibrate()
        threading.Thread(target=clock_motor_thread).start()
