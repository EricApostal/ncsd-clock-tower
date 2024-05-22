
# Max amount of time a motor can move until it just continues
motor_timeout = 10

photo_sensor_port = 16
motor_port = 37

import RPi.GPIO as GPIO
import time, threading, atexit, sys, os

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

current_step = 0
current_state = None
program_running = True
_serial = None
last_step_path = "/home/raspberrypi/Documents/last_step.txt"

"""
Listen for changes in the digital signal from the photo sensor
"""
def serial_thread():
    GPIO.setup(photo_sensor_port, GPIO.IN)
    global current_state, program_running

    while True:
        if (not program_running):
            return
        
        new_state = GPIO.input(photo_sensor_port)
        if (current_state == None):
            current_state = new_state
            # print("Initial light state: " + str(new_state))
            continue

        if new_state != current_state:
            # print("Light state changed to: " + str(new_state))
            current_state = new_state

"""
Runs on program exit. Used to prevent potential GPIO errors.
"""
def exit_handler():
    print("    Cleaning up...")
    GPIO.cleanup()

def init_last_step_file():
    try:
        with open(last_step_path, "r") as f:
            return
    except FileNotFoundError:
        with open(last_step_path, "w") as f:
            f.write("0")

def write_last_step(state: int):
    with open(last_step_path, "w") as f:
        f.write(str(state))

def read_last_step():
    with open(last_step_path, "r") as f:
        return int(f.read())

"""
Move the motor a certain number of steps
Each step represents 30 seconds
"""
def move_steps(steps: int):
    if (int(steps) == 0):
        return
    
    global current_step

    GPIO.setup(motor_port, GPIO.OUT)
    for _ in range(int(steps)):
        last_state = current_state
        started_moving_time = time.time()
        while (current_state == last_state):
            if (time.time() - started_moving_time) >= motor_timeout:
                print("Step move timed out. This is bad, the light sensor is probably misreading.")
                break # maybe should exit here
            time.sleep(0.1)

            GPIO.output(motor_port, GPIO.HIGH)

        current_step += 1

        # 1440 is the number of steps in 12 hours
        # Once we reach 1440, we're back at 12:00
        if (current_step == 1440):
            current_step = 0

        _curr_min = str(int((current_step / 2) % 60))
        if (len(_curr_min) == 1):
            _curr_min = "0" + _curr_min

        step_time_formatted = str(int(current_step / 2 / 60)) + ":" + _curr_min
        print("Moved to time " + str(step_time_formatted))
        write_last_step(current_step)

    GPIO.output(motor_port, GPIO.LOW)

def _sanitize_minute(minute: int):
    # we want to translate every time to a 12 hour scale to prevent excess
    # movement (since a clock only has 12 hours, and a day has 24)

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
    What time does the clock tower currently display? Do not include AM/PM units.
    Ex: 9:32
    """)

    current_minute_of_day = _sanitize_minute(int(time.strftime("%H")) * 60 + int(time.strftime("%M")))

    current_clock_minute = str(input("    [USER]: "))
    current_clock_minute = _sanitize_minute(int(current_clock_minute.split(":")[0]) * 60 + int(current_clock_minute.split(":")[1]))

    write_last_step(_sanitize_minute(current_clock_minute) * 2)

    new_hour = int(current_minute_of_day / 60)
    new_minute = current_minute_of_day % 60
    print("    Clock has been calibrated to " + str(new_hour) + ":" + str(new_minute))

def clock_motor_thread():
    while True:
        target_minute = _sanitize_minute(int(time.strftime("%H")) * 60 + int(time.strftime("%M")))
        step_count = _calculate_steps(current_step/2, target_minute)

        if (step_count > 0):
            print("Moving " + str(step_count) + " steps")
            move_steps(step_count)

        time.sleep(0.1)

"""
Takes the last known step and moves the hand to where it should be
"""
def boot_recalibrate():
    global current_step
    current_step = read_last_step()

def spawn_user_menu():
    global program_running

    os.system('clear')
    print(r"""
     _   _  _____  _____ _____      _____ _      ____   _____ _  __
    | \ | |/ ____|/ ____|  __ \    / ____| |    / __ \ / ____| |/ /
    |  \| | |    | (___ | |  | |  | |    | |   | |  | | |    | ' / 
    | . ` | |     \___ \| |  | |  | |    | |   | |  | | |    |  <  
    | |\  | |____ ____) | |__| |  | |____| |___| |__| | |____| . \ 
    |_| \_|\_____|_____/|_____/    \_____|______\____/ \_____|_|\_\
          
    Programmed by Eric Apostal and Christopher Holley
    Powered by NCSSM
    """)
    
    print("""
    Welcome to the clock control panel. What would you like to do?
    [1] Calibrate the clock
    [2] Start the clock service
    [3] Stop the clock service
    """)

    """
    Info:
    (1) Calibrating the clock will allow you to set the clock to a certain time. You should ideally only have to do this once ever.
    (2) Starting the clock will just start the clock from the last known position. While you can start it manually, it should already be running right now.
    (3) Stopping the clock will stop the clock from running. You can start it again by re-opening this menu, and selecting option 2.
    (4) Set the system time.
    """

    acceptable_input = ["1", "2", "3", "4"]
    user_input = input("    [USER]: ")

    while user_input not in acceptable_input:
        print("    Invalid input. Please try again.")
        user_input = input("    [USER]: ")
    
    if user_input == "1":
        os.system('sudo systemctl stop clock.service')
        print("    Calibrating...")
        initialize_position()
        GPIO.cleanup()
        os.system('sudo systemctl start clock.service')
        print("    Clock has been calibrated, and it is now running! You can close this now.")
    elif user_input == "2":
        os.system('sudo systemctl restart clock.service')
        print("    Started clock service!")
        
        print("    Error starting clock service. Assuming it's enabled already.")
        print("    Service is running! You can close this now. Feel free to check on the service by running 'sudo systemctl status clock.service'.")
    elif user_input == "3":
        os.system('sudo systemctl stop clock.service')
        print("    Stopped clock service. You can close this now.")
    elif user_input == "4":
        print("Setting the time isn't implemented yet! If you are the user and recieve this error message, sorry! I meant to implement this.")
        # os.system('sudo date')
        # print("    System time has been set. You can close this now.")

    print("    Everything executed successfully! This menu will close in 3 seconds...")
    time.sleep(3)

    program_running = False
    _serial.join()

if __name__ == '__main__':
    print("Starting clock...")
    if (len(sys.argv) > 2):
        ValueError("Usage: python3 main.py -c (pass -c if you want to calibrate, otherwise leave blank)")

    atexit.register(exit_handler)
    init_last_step_file()

    _serial = threading.Thread(target=serial_thread)
    _serial.start()

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
