""""
flask API for raspberry pi
example from http://www.pibits.net/code/raspberry-pi-sht31-sensor-example.php
"""
# Flask imports
from flask import Flask, request, send_from_directory
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

# built-in imports
import os
import statistics
import sys
import time

# local imports
import sht31_config
import utilities as util

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


class Sensors(object):

    def __init__(self):
        pass

    def convert_data(self, data):
        """
        Convert data from bits to real units.

        inputs:
            data(class 'list'): raw data structure
        returns:
            temp(int): raw temp data in bits.
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
        return {sht31_config.API_MEASUREMENT_CNT: len(fTemp_lst),
                sht31_config.API_TEMPC_MEAN:  statistics.mean(cTemp_lst),
                sht31_config.API_TEMPC_STD: statistics.pstdev(cTemp_lst),
                sht31_config.API_TEMPF_MEAN: statistics.mean(fTemp_lst),
                sht31_config.API_TEMPF_STD: statistics.pstdev(fTemp_lst),
                sht31_config.API_HUMIDITY_MEAN: statistics.mean(humidity_lst),
                sht31_config.API_HUMIDITY_STD: statistics.pstdev(humidity_lst),
                }

    def set_sht31_address(self, i2c_addr, addr_pin, alert_pin):
        """
        Set the address for the sht31.

        inputs:
            i2c_addr(int): bus address of SHT31.
            addr_pin(int):
            alert_pin(int):
        returns:
            None
        """
        # set address pin on SHT31
        GPIO.setmode(GPIO.BCM)  # broadcom pin numbering
        GPIO.setup(addr_pin, GPIO.OUT)  # address pin set as output
        GPIO.setup(alert_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        if i2c_addr == 0x45:
            GPIO.output(addr_pin, GPIO.HIGH)
        else:
            GPIO.output(addr_pin, GPIO.LOW)

    def send_i2c_cmd(self, bus, i2c_addr, i2c_command):
        """
        Send the i2c command to the sht31.

        inputs:
            bus(class 'SMBus'): i2c bus object
            i2c_addr(int):  bus address
            i2c_command(tuple): command (register, [data])
        returns:
            None
        """
        register = i2c_command[0]
        data = i2c_command[1]
        try:
            bus.write_i2c_block_data(i2c_addr, register, data)
        except OSError as e:
            print("FATAL ERROR(%s): i2c device at address %s is "
                  "not responding" %
                  (util.get_function_name(), hex(i2c_addr)))
            raise e
        time.sleep(0.5)

    def read_i2c_data(self, bus, i2c_addr, register=0x00, length=0x06):
        """
        Read i2c data.

        inputs:
            bus(class 'SMBus'): i2c bus object
            i2c_addr(int):  bus address
            register(int): register to read from.
            length(int):  number of blocks to read.
        returns:
            response(class 'list'): raw data structure
        """
        # Temp MSB, temp LSB, temp CRC, humidity MSB,
        # humidity LSB, humidity CRC
        # read_i2c_block_data(i2c_addr, register, length,
        #                     force=None)
        try:
            response = bus.read_i2c_block_data(i2c_addr,
                                               register,
                                               length)
        except OSError as e:
            print("FATAL ERROR(%s): i2c device at address %s is "
                  "not responding" %
                  (util.get_function_name(), hex(i2c_addr)))
            raise e
        return response

    def parse_fault_register_data(self, data):
        """
        Parse the fault register data, if possible.

        inputs:
            data(): list containing at least 2 bytes.
                    3rd byte (checksum) is not currently used.
        returns:
            (dict): fault register contents.
        """
        try:
            d = data[0] * 256 + data[1]
            resp = {
                'raw': data,
                'raw_binary': format(d, '#018b')[2:],
                'alert pending status(0=0,1=1+)': (d >> 15) & 1,
                # bit 15: 0=None, 1=at least 1 pending alert
                'heater status(0=off,1=on)': (d >> 13) & 1,
                # bit 13: 0=off, 1=on
                'RH tracking alert(0=no,1=yes)': (d >> 11) & 1,
                # bit 11: 0=no, 1=yes
                'T tracking alert(0=no,1=yes)': (d >> 10) & 1,
                # bit 10: 0=no, 1=yes
                'System reset detected(0=no,1=yes)': (d >> 4) & 1,
                # bit 4
                # 0=no reset since last clear cmd, 1=hard, soft, or supply fail
                'Command status(0=correct,1=failed)': (d >> 1) & 1,
                # bit 1: 0=successful, 1=invalid or field checksum
                'Write data checksum status(0=correct,1=failed)': (d >> 0) & 1,
                # bit 0: 0=correct, 1=failed
                }
        except IndexError:
            # parsing error, just return raw data
            print("WARNING: fault register parsing error, just returning "
                  "raw fault register data")
            resp = {'raw': data}
        return resp

    def get_unit_test(self):
        """
        Get fabricated data for unit testing at ip:port/unit.

        syntax: http://ip:port/unit?seed=0x7E&measurements=1
        inputs:
            None
        returns:
            (dict): fabricated unit test data.
        """
        # get runtime parameters
        measurements = request.args.get('measurements',
                                        sht31_config.measurements,
                                        type=int)
        seed = request.args.get('seed', sht31_config.unit_test_seed, type=int)

        # data structure
        fTemp_lst = []
        cTemp_lst = []
        humidity_lst = []

        # loop for n measurements
        for m in range(measurements):

            # fabricated data for unit testing
            data = [seed + m % 2] * 5  # almost mid range

            # convert the data
            _, cTemp, fTemp, humidity = self.convert_data(data)

            # add data to structure
            fTemp_lst.append(fTemp)
            cTemp_lst.append(cTemp)
            humidity_lst.append(humidity)

        # return data on API
        return self.pack_data_structure(fTemp_lst, cTemp_lst, humidity_lst)

    def get(self):
        """
        Get sensor data at ip:port.

        inputs:
            None
        returns:
            (dict): thermal data dictionary.
        """
        # get runtime parameters
        measurements = request.args.get('measurements', 1, type=int)

        # set address pin on SHT31
        self.set_sht31_address(sht31_config.i2c_address, sht31_config.addr_pin,
                               sht31_config.alert_pin)

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
                self.send_i2c_cmd(bus, sht31_config.i2c_address,
                                  cs_enabled_high)

                # read the measurement data
                data = self.read_i2c_data(bus, sht31_config.i2c_address,
                                          register=0x00, length=0x06)

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

    def send_cmd_get_diag(self, i2c_command):
        """
        Send i2c command and read status register..

        inputs:
            i2c_command(int): i2c command to send
        returns:
            (dict): parsed fault register data.
        """
        # set address pin on SHT31
        self.set_sht31_address(sht31_config.i2c_address, sht31_config.addr_pin,
                               sht31_config.alert_pin)

        # activate smbus
        bus = smbus.SMBus(1)
        time.sleep(0.5)

        try:
            # send single shot command
            self.send_i2c_cmd(bus, sht31_config.i2c_address,
                              i2c_command)

            # small delay
            time.sleep(1.0)

            # read the measurement data, 2 bytes data, 1 byte checksum
            data = self.read_i2c_data(bus, sht31_config.i2c_address,
                                      register=0x00, length=0x03)

            # parse data into registers
            parsed_data = self.parse_fault_register_data(data)
            return parsed_data
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


class ReadFaultRegister(Resource):
    """Diagnostic Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(read_status_register)


class ClearFaultRegister(Resource):
    """Clear Diagnostic Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(clear_status_register)


class EnableHeater(Resource):
    """Enable heater Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(enable_heater)


class DisableHeater(Resource):
    """Enable heater Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(disable_heater)


class SoftReset(Resource):
    """Enable heater Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(soft_reset)


class Reset(Resource):
    """Enable heater Controller."""
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.send_cmd_get_diag(reset)


def create_app():

    app_ = Flask(__name__)

    # add API routes
    api = Api(app_)
    api.add_resource(Controller, "/")
    api.add_resource(ControllerUnit, sht31_config.flask_folder.unit_test)
    api.add_resource(ReadFaultRegister, sht31_config.flask_folder.diag)
    api.add_resource(ClearFaultRegister, sht31_config.flask_folder.clear_diag)
    api.add_resource(EnableHeater, sht31_config.flask_folder.enable_heater)
    api.add_resource(DisableHeater, sht31_config.flask_folder.disable_heater)
    api.add_resource(Reset, sht31_config.flask_folder.reset)
    api.add_resource(SoftReset, sht31_config.flask_folder.soft_reset)
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


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'image'),
                               'sht31.ico',
                               mimetype='image/vnd.microsoft.icon')


def parse_runtime_parameters():
    """Parse runtime parameters."""
    # parse runtime parameters, argv[1] is flask server debug mode
    debug_flag = False  # default
    if len(sys.argv) > 1:
        argv3_str = sys.argv[1]
        if argv3_str.lower() in ["1", "true"]:
            debug_flag = True
            print("Flask debug mode is enabled", file=sys.stderr)
    return debug_flag


if __name__ == "__main__":

    print("SHT31 sensor Flask server")

    # verify environment
    util.get_python_version()

    # parse runtime parameters
    debug = parse_runtime_parameters()

    # launch the Flask API on development server
    app.run(host='0.0.0.0',
            port=sht31_config.flask_port,
            debug=debug,
            threaded=True,  # threaded=True may speed up rendering on web page
            ssl_context=sht31_config.flask_ssl_cert)
