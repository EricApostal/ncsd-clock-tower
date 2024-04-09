import RPi.GPIO as GPIO
import time, serial, threading, atexit, sys, os

ser = serial.Serial('/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_85734323430351600190-if00', 9600, timeout=1)
ser.reset_input_buffer()

close_threads = False

GPIO.setwarnings(False)

# The light value that will signal a change in state
light_threshold = 300
current_step = 0

# this should be 60, but it might be nice to set lower for testing
minute_seconds = 10

current_state = None

"""
Listens for raw analog light resistance values from the Arduino
"""
def serial_thread():
    global current_state

    while True:
        if(close_threads):
            sys.exit()

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

def init_last_step_file():
    try:
        with open("/home/pi/Documents/last_step.txt", "r") as f:
            print("Last step file already exists")
            return
    except FileNotFoundError:
        with open("/home/pi/Documents/last_step.txt", "w") as f:
            print("Last step file created")
            f.write("0")

def write_last_step(state: int):
    with open("/home/pi/Documents/last_step.txt", "w") as f:
        f.write(str(state))

def read_last_step():
    with open("/home/pi/Documents/last_step.txt", "r") as f:
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
            time.sleep(0.01)
        current_step += 1
        print("stepped")

        # 720 is the number of steps in 12 hours
        # Once we reach 720, we're back at 12:00
        if (current_step == 720):
            current_step = 0

        print("writing last step")
        write_last_step(current_step)
        print("wrote last step")

    GPIO.output(motor, GPIO.LOW)

def _sanitize_minute(minute: int):
    if (minute >= 720):
        minute -= 720
    return minute

def _calculate_steps(current_minute: int, target_minute: int):
    steps = (target_minute - current_minute) * 2
    if (steps < 0):
        steps = 1440 + steps
    return steps

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

    current_clock_minute = str(input("    [USER]: "))
    current_clock_minute = _sanitize_minute(int(current_clock_minute.split(":")[0]) * 60 + int(current_clock_minute.split(":")[1]))

    current_step = _sanitize_minute(current_clock_minute * 2)

    steps_to_move = _calculate_steps(current_step/2, current_minute_of_day)
    print("    [Initialization] Steps to move: " + str(steps_to_move))

    target_steps = 2

    while int(target_steps) > 1:
        # print("The clock is not displaying the correct time, moving " + str(target_steps) + " steps to correct it")
        move_steps(target_steps)
        target_steps = _calculate_steps(current_step / 2, current_minute_of_day)

    new_hour = int(current_minute_of_day / 60)
    new_minute = current_minute_of_day % 60
    print("    Clock has been calibrated to " + str(new_hour) + ":" + str(new_minute))

def clock_motor_thread():
    time.sleep(minute_seconds)
    while True:
        start_time = time.time()
        move_steps(2)
        end_time = time.time()

        diff = minute_seconds - (end_time - start_time)

        if diff > 0:
            time.sleep(diff)
        else:
            print("""Motor took too long to move. Maybe a sensor error?
                  This error is critical! My guess as to what happened is that
                  the sensor isn't reading properly, so it thinks nothing has moved.
                  """)

"""
last_state represents the last step
find the step we are on, and move the motor to that step
"""
def boot_recalibrate():
    global current_step

    current_step = read_last_step()
    print("Last step: " + str(current_step))
    current_minute_of_day = int(time.strftime("%H")) * 60 + int(time.strftime("%M"))
    target_step = _sanitize_minute(current_minute_of_day) * 2
    step_count = _calculate_steps(current_step, target_step)
    print("Recalibrating to step: " + str(target_step) + " with " + str(step_count) + " steps")
    move_steps(step_count)

def spawn_user_menu():
    os.system('clear')
    print("""
    _   _  _____  _____ _____     _____ _      ____   _____ _  __  _______ ______          ________ _____  
    | \ | |/ ____|/ ____|  __ \   / ____| |    / __ \ / ____| |/ / |__   __/ __ \ \        / /  ____|  __ \ 
    |  \| | |    | (___ | |  | | | |    | |   | |  | | |    | ' /     | | | |  | \ \  /\  / /| |__  | |__) |
    | . ` | |     \___ \| |  | | | |    | |   | |  | | |    |  <      | | | |  | |\ \/  \/ / |  __| |  _  / 
    | |\  | |____ ____) | |__| | | |____| |___| |__| | |____| . \     | | | |__| | \  /\  /  | |____| | \ \ 
    |_| \_|\_____|_____/|_____/   \_____|______\____/ \_____|_|\_\    |_|  \____/   \/  \/   |______|_|  \_\                                                                                                                                                                                             
    
    Powered by NCSSM
    """)
    print("""
    Welcome to the clock control panel. What would you like to do?
    [1] Calibrate the clock
    [2] Just start the clock
          
    Info:
    (1) Calibrating the clock will allow you to set the clock to a certain time. You should ideally only have to do this once ever.
    (2) Starting the clock will just start the clock from the last known position. While you can start it manually, it should
    already be running right now.
    """)

    acceptable_input = ["1", "2"]
    user_input = input("    [USER]: ")

    if user_input not in acceptable_input:
        print("    Invalid input. Please try again.")
        user_input = input("    [USER]: ")
    
    if user_input == "1":
        os.system('sudo systemctl stop clock.service')
        print("    Calibrating...")
        initialize_position()
        GPIO.cleanup()
        os.system('sudo systemctl start clock.service')
        print("    Clock has been calibrated! You can close this now.")
        return
    else:
        try:
            os.system('sudo systemctl start clock.service')
            print("    Started clock service!")
        except:
            print("    Error starting clock service. Assuming it's enabled already.")
        print("    Service is running! You can close this now. Feel free to check on the service by running 'sudo systemctl status clock.service'.")

if __name__ == '__main__':
    if (len(sys.argv) > 2):
        ValueError("Usage: python3 main.py -c (pass -c if you want to callibrate, otherwise leave blank)")

    atexit.register(exit_handler)
    init_last_step_file()

    serial_thread = threading.Thread(target=serial_thread)
    serial_thread.start()
    time.sleep(1)

    if (len(sys.argv) == 2):
        if (sys.argv[1] == "-c"):
            print("Calibrating...")
            initialize_position()
        elif (sys.argv[1] == "-m"):
            spawn_user_menu()
    else:
        print("Starting clock...")
        boot_recalibrate()
        print("Clock has been calibrated, running motor listener")
        threading.Thread(target=clock_motor_thread).start()
