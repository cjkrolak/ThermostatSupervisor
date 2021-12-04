""""
flask API for raspberry pi
example from http://www.pibits.net/code/raspberry-pi-sht31-sensor-example.php
"""
from flask import Flask
from flask_restful import Resource, Api  # noqa F405
from flask_wtf.csrf import CSRFProtect

# raspberry pi libraries
try:
    import RPi.GPIO as GPIO  # noqa F405 raspberry pi GPIO library
    import smbus  # noqa F405
    pi_library_exception = None  # successful
except ImportError as e:
    # hardware-related library, not needed in unittest mode
    print("WARNING: RPi or smbus library import error, "
          "this is expected in unittest mode")
    pi_library_exception = e  # unsuccessful
import statistics
import sys
import time

# local imports
import utilities as util


# SHT31D config
i2c_address = 0x45  # i2c address b

# SHT31D write commands (register, [data])
# spec: https://cdn-shop.adafruit.com/product-files/
# 2857/Sensirion_Humidity_SHT3x_Datasheet_digital-767294.pdf

# single shot mode: clock_stretching, repeatability
cs_enabled_high = (0x2c, [0x06])
cs_enabled_med = (0x2c, [0x0d])
cs_enabled_low = (0x2c, [0x10])
cs_disabled_high = (0x24, [0x00])
cs_disabled_med = (0x24, [0x0b])
cs_disabled_low = (0x24, [0x16])

# periodic data acquisition modes: mps, repeatability
mps_0p5_high = (0x20, [0x32])
mps_0p5_med = (0x20, [0x24])
mps_0p5_low = (0x20, [0x2f])
mps_1_high = (0x21, [0x30])
mps_1_med = (0x21, [0x26])
mps_1_low = (0x21, [0x2d])
mps_2_high = (0x22, [0x36])
mps_2_med = (0x22, [0x20])
mps_2_low = (0x22, [0x2b])
mps_4_high = (0x23, [0x34])
mps_4_med = (0x23, [0x22])
mps_4_low = (0x23, [0x29])
mps_10_high = (0x27, [0x37])
mps_10_med = (0x27, [0x21])
mps_10_low = (0x27, [0x2a])

# misc commands
fetch_data = (0xe0, [0x00])
period_meas_with_art = (0x2b, [0x32])
break_periodic_data = (0x30, [0x93])
soft_reset = (0x30, [0xa2])
reset = (0x00, [0x06])
enable_heater = (0x30, [0x6d])
disable_heater = (0x30, [0x66])
clear_status_register = (0x30, [0x41])
read_status_register = (0xf3, [0x2d])


# pi0 config
alert_pin = 17  # yellow wire, GPIO17 (pi pin 11)
addr_pin = 4  # white wire, GPIO4, low = 0x44, high=0x45 (pi pin 7)


class Sensors(object):

    def __init__(self):
        pass

    def convert_data(self, data):
        """
        Convert data from bits to real units.

        inputs:
            data: data structure
        returns:
            temp(float): raw temp
            cTemp(float): temp on deg C
            fTemp(float): temp in deg F
            humidity(float): humidity in %RH
        """
        # convert the data
        temp = data[0] * 256 + data[1]
        cTemp = -45 + (175 * temp / 65535.0)
        fTemp = -49 + (315 * temp / 65535.0)
        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
        return temp, cTemp, fTemp, humidity

    def pack_data_structure(self, fTemp_lst, cTemp_lst, humidity_lst):
        """
        Calculate statistics and pack data structure.

        inputs:
            fTemp_lst(list): list of fehrenheit measurements
            cTemp_lst(list): list of celcius measurements
            humidity_lst(list): list of humidity measurements.
        returns:
            (dict): data structure.
        """
        return {
                'measurements': len(fTemp_lst),  # number of measurements
                'Temp(C) mean':  statistics.mean(cTemp_lst),
                'Temp(C) std': statistics.pstdev(cTemp_lst),
                util.API_TEMP_FIELD: statistics.mean(fTemp_lst),
                'Temp(F) std': statistics.pstdev(fTemp_lst),
                util.API_HUMIDITY_FIELD: statistics.mean(humidity_lst),
                'Humidity(%RH) std': statistics.pstdev(humidity_lst),
                }

    def get_unit_test(self):
        """Get fabricated data for unit testing."""
        # data structure
        fTemp_lst = []
        cTemp_lst = []
        humidity_lst = []

        # loop for n measurements
        for m in range(measurements):

            # fabricated data for unit testing
            data = [0x7F + m % 2] * 5  # almost mid range

            # convert the data
            _, cTemp, fTemp, humidity = self.convert_data(data)

            # add data to structure
            fTemp_lst.append(fTemp)
            cTemp_lst.append(cTemp)
            humidity_lst.append(humidity)

        # return data on API
        return self.pack_data_structure(fTemp_lst, cTemp_lst, humidity_lst)

    def set_sht31_address(self):
        """Set the address for the sht31."""
        # set address pin on SHT31
        GPIO.setmode(GPIO.BCM)  # broadcom pin numbering
        GPIO.setup(addr_pin, GPIO.OUT)  # address pin set as output
        GPIO.setup(alert_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if i2c_address == 0x45:
            GPIO.output(addr_pin, GPIO.HIGH)
        else:
            GPIO.output(addr_pin, GPIO.LOW)

    def send_i2c_cmd(self, bus, i2c_command):
        """
        Send the i2c command to the sht31.

        inputs:
            bus(obj?): i2c bus object
            i2c_command(tuple): (register, [data])
        returns:
            None
        """
        # write_i2c_block_data(i2c_addr, register, data,
        #                      force=None)
        register = i2c_command[0]
        data = i2c_command[1]
        bus.write_i2c_block_data(i2c_address, register, data)
        time.sleep(0.5)

    def read_i2c_data(self, bus, register=0x00, length=0x06):
        """
        Read i2c data.

        inputs:
            bus(obj?): i2c bus object
            register(int): register to read from.
            length(int):  number of blocks to read.
        returns:
            data
        """
        # Temp MSB, temp LSB, temp CRC, humidity MSB,
        # humidity LSB, humidity CRC
        # read_i2c_block_data(i2c_addr, register, length,
        #                     force=None)
        return bus.read_i2c_block_data(i2c_address, register,
                                       length)

    def get(self):
        """Get sensor data."""

        # set address pin on SHT31
        self.set_sht31_address()

        # activate smbus
        bus = smbus.SMBus(1)
        time.sleep(0.5)

        # data structure
        fTemp_lst = []
        cTemp_lst = []
        humidity_lst = []

        try:
            # loop for n measurements
            for _ in range(measurements):
                # send single shot read command
                self.send_i2c_cmd(bus, cs_enabled_high)

                # read the measurement data
                data = self.read_i2c_data(bus, register=0x00, length=0x06)

                # convert the data
                _, cTemp, fTemp, humidity = self.convert_data(data)

                # add data to structure
                fTemp_lst.append(fTemp)
                cTemp_lst.append(cTemp)
                humidity_lst.append(humidity)

            # return data on API
            return self.pack_data_structure(fTemp_lst, cTemp_lst, humidity_lst)
        finally:
            # close the smbus connection
            bus.close()
            GPIO.cleanup()  # clean up GPIO

    def get_diag(self):
        """Get status register data."""

        # set address pin on SHT31
        self.set_sht31_address()

        # activate smbus
        bus = smbus.SMBus(1)
        time.sleep(0.5)

        try:
            # send single shot read command
            self.send_i2c_cmd(bus, read_status_register)

            # read the measurement data
            data = self.read_i2c_data(bus, register=0x00, length=0x06)

            # parsed_data = {
            #     }
            # return data on API
            return data
        finally:
            # close the smbus connection
            bus.close()
            GPIO.cleanup()  # clean up GPIO


class Controller(Resource):
    """Production controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.get()


class ControllerUnit(Resource):
    """Unit test Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.get_unit_test()


class ControllerDiag(Resource):
    """Diagnostic Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.get_diag()


def create_app():

    app_ = Flask(__name__)

    # add API routes
    api = Api(app_)
    api.add_resource(Controller, "/")
    api.add_resource(ControllerUnit, util.FLASK_UNIT_TEST_FOLDER)
    api.add_resource(ControllerDiag, "/diag")
    return app_


# create the flask app
app = create_app()
csrf = CSRFProtect(app)  # enable CSRF protection

# protect against cookie attack vectors in our Flask configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)


if __name__ == "__main__":

    unit_test_mode = False
    print("SHT31 sensor Flask server")

    # parse runtime parameters, argv[1] is unittest mode
    if len(sys.argv) > 1 and sys.argv[1] == "unittest":
        unit_test_mode = True
        print("Running in unit test mode (fabricated output)", file=sys.stderr)
    else:
        print("Running in production mode (real output)", file=sys.stderr)
        # raise exception if pi libaries failed to load
        if pi_library_exception is not None:
            raise pi_library_exception

    # argv[2] is measurement count
    if len(sys.argv) > 2:
        measurements = int(sys.argv[2])
    else:
        measurements = 1  # default
    print("Averaging %s measurement for each reading" %
          measurements, file=sys.stderr)

    # argv[3] is flask server debug mode
    debug = False  # default
    if len(sys.argv) > 3:
        argv3_str = sys.argv[3]
        if argv3_str.lower() in ["1", "true"]:
            debug = True
            print("Flask debug mode is enabled", file=sys.stderr)

    # launch the Flask API
    app.run(debug=debug, host='0.0.0.0')
