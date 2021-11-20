""""flask API for raspberry pi"""
from flask import Flask
from flask_restful import Resource, Api  # noqa F405
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
i2c_address = 0x45

# pi0 config
alert_pin = 17  # yellow wire, GPIO17 (pi pin 11)
addr_pin = 4  # white wire, GPIO4, low = 0x44, high=0x45 (pi pin 7)


class Sensors(object):

    def __init__(self):
        pass

    def get(self):

        if not unit_test_mode:
            # set address pin on SHT31
            GPIO.setmode(GPIO.BCM)  # broadcom pin numbering
            GPIO.setup(addr_pin, GPIO.OUT)  # address pin set as output
            GPIO.setup(alert_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            if i2c_address == 0x45:
                GPIO.output(addr_pin, GPIO.HIGH)
            else:
                GPIO.output(addr_pin, GPIO.LOW)

            # activate smbus
            bus = smbus.SMBus(1)

        # data structure
        fTemp_lst = []
        cTemp_lst = []
        humidity_lst = []

        try:
            # loop for n measurements
            for m in range(measurements):
                # SHT31 address
                if not unit_test_mode:
                    bus.write_i2c_block_data(i2c_address, 0x2c, [0x06])
                    time.sleep(0.5)

                # SHT31 address 0x44(68)
                # read data back from 0x00(00), 6 bytes
                # Temp MSB, temp LSB, temp CRC, humidity MSB,
                #     humidity LSB, humidity CRC
                if not unit_test_mode:
                    data = bus.read_i2c_block_data(i2c_address, 0x00, 6)
                else:
                    # fabricated data for unit testing
                    data = [0x7F + m % 2] * 5  # mid range

                # convert the data
                temp = data[0] * 256 + data[1]
                cTemp = -45 + (175 * temp / 65535.0)
                fTemp = -49 + (315 * temp / 65535.0)
                humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

                # add data to structure
                fTemp_lst.append(fTemp)
                cTemp_lst.append(cTemp)
                humidity_lst.append(humidity)

                # output the data to screen
                # print("\nmeasurement #%s of %s" % (n, measurements))
                # print("Temperature in celsius is: %.2f C" % cTemp)
                # print("Temperature in Fahrenheit is: %.2f F" % fTemp)
                # print("Relative Humidty is: %.2f %%RH" % humidity)

            # return data on API
            return {
                'measurements': len(fTemp_lst),  # number of measurements
                'Temp(C) mean':  statistics.mean(cTemp_lst),
                'Temp(C) std': statistics.pstdev(cTemp_lst),
                util.API_TEMP_FIELD: statistics.mean(fTemp_lst),
                'Temp(F) std': statistics.pstdev(fTemp_lst),
                util.API_HUMIDITY_FIELD: statistics.mean(humidity_lst),
                'Humidity(%RH) std': statistics.pstdev(humidity_lst),
                }
        finally:
            if not unit_test_mode:
                # close the smbus connection
                bus.close()
                GPIO.cleanup()  # clean up GPIO


class Controller(Resource):
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.get()


def create_app():

    app_ = Flask(__name__)
    api = Api(app_)

    api.add_resource(Controller, "/")
    return app_


# create the flask app
app = create_app()


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
