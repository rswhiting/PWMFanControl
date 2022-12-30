#!/usr/bin/env python3
# File name: MultiFanController.py
# Author: Robert Whiting
# Date: 2022-12-30
#
# Description: Raspberry Pi fan controller based on the work of Michael Klements https://github.com/mklements/PWMFanControl

import argparse
import logging as log
import RPi.GPIO                # Calling GPIO to allow use of the GPIO pins
import subprocess              # Calling subprocess to get the CPU temperature
import sys
import time                    # Calling time to allow delays to be used
import yaml

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
class v:
    SUCCESS = bcolors.OKGREEN + '\u2713' + bcolors.ENDC + "  "     # Green checkmark
    FAIL = bcolors.FAIL + '\u2622' + bcolors.ENDC + "  "           # ☢ failure
    LIST = bcolors.WARNING + '\u2192' + bcolors.ENDC + "  "        # → arrow pointing
    NOTE = bcolors.OKCYAN + '\u259E' + bcolors.ENDC + "  "         # ▞ Note
    DEBUG = bcolors.WARNING + '\u26A1' + bcolors.ENDC + " "        # ⚡ Lightning bolt



def parse_arguments():
    parser = argparse.ArgumentParser(description='Arguments get parsed via --commands')
    parser.add_argument('-v', type=int, default=4,
        help='Verbosity of logging: 0-critical, 1-error, 2-warning, 3-info, 4-debug')
    parser.add_argument('--test', default=False, action="store_true",
        help='Test mode for testing pinout and fan control, defaults to False')
    parser.add_argument('--conf', type=str, default='config.yaml',
        help='Config file, defaults to config.yaml')

    args = parser.parse_args()
    verbose = {0: log.CRITICAL, 1: log.ERROR, 2: log.WARNING, 3: log.INFO, 4: log.DEBUG}
    log.basicConfig(format='%(message)s', level=verbose[args.v], stream=sys.stdout)
    
    return args



def get_temp():                              # Function to read in the CPU temperature and return it as a float in degrees celcius
    output = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True)
    temp_str = output.stdout.decode()
    try:
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError):
        raise RuntimeError('Could not get temperature')



def setup_fans(config):
    RPi.GPIO.setwarnings(False)          # Do not show any GPIO warnings
    RPi.GPIO.setmode (RPi.GPIO.BCM)            # BCM pin numbers - PIN8 as ‘GPIO14’
    fans = []
    for fan in config['fans']:
        RPi.GPIO.setup(fan['gpio'], RPi.GPIO.OUT)      # Initialize GPIO14 as our fan output pin
        fan = RPi.GPIO.PWM(fan['gpio'], fan['hz'])  # Set GPIO14 as a PWM output, with 100Hz frequency (this should match your fans specified PWM frequency)
        fan.start(0)                          # Generate a PWM signal with a 0% duty cycle (fan off)
        fans.append(fan)
    return fans



def test_mode(config, fans):
    log.info(v.NOTE + "Running in test mode")
    # this will ramp up each fan to the max then turn it off one at a time
    for idx, fan in enumerate(config['fans']):
        duty_cycles = list(config['temp_to_duty_cycle_thresholds'].values())
        for duty_cycle in duty_cycles:
            log.debug(v.DEBUG + " Changing fan {} to {}%".format(idx, duty_cycle))
            # fan[idx].ChangeDutyCycle(duty_cycle)
            time.sleep(config['timeout_seconds'])
        # fan[idx].ChangeDutyCycle(0)
    pass



def temp_to_duty_cycle(config, temp):
    lookup = config['temp_to_duty_cycle_thresholds']
    thresholds = list(lookup.keys())
    target = 0
    for threshold in thresholds:
        if temp >= threshold and threshold > target:
            target = threshold
    return lookup[target]



def main(args):
    with open(args.conf, 'r') as file:
        config = yaml.safe_load(file)['config']

    fans = setup_fans(config)

    if (args.test):
        test_mode(config, fans)
    else:
        # primary execution loop
        while (1):
            # get temp
            temp = get_temp()
            log.debug(v.DEBUG + "Current temperature {}°C".format(temp))

            # identify duty cycle
            duty_cycle = temp_to_duty_cycle(config, temp)
            # for x in [12,24,34,43,59,60,61, 88, 109]:
            #     log.debug("for temp {}, set duty to {}".format(x, temp_to_duty_cycle(config, x)))

            # set duty cycle on all fans
            for idx, fan in enumerate(config['fans']):
                log.debug(v.DEBUG + " Changing fan {} to {}%".format(idx, duty_cycle))
                fans[idx].ChangeDutyCycle(duty_cycle)

            time.sleep(config['timeout_seconds'])
        pass



if __name__ == '__main__':
    args = parse_arguments()
    main(args)