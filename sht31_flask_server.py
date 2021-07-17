# flask API for raspberry pi
from flask import Flask
from flask_restful import Resource, Api  # noqa F405
import RPi.GPIO as GPIO  # noqa F405 raspberry pi GPIO library
import smbus  # noqa F405
import statistics
import time

# local imports
import utilities as util


app = Flask(__name__)
api = Api(app)

# SHT31D config
i2c_address = 0x45
measurements = 1  # number of measurements to average

# pi0 config
alert_pin = 17  # yellow wire, GPIO17 (pi pin 11)
addr_pin = 4  # white wire, GPIO4, low = 0x44, high=0x45 (pi pin 7)


class Sensors(object):

    def __init__(self):
        pass

    def get(self):

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
            for _ in range(measurements):
                # SHT31 address
                bus.write_i2c_block_data(i2c_address, 0x2c, [0x06])

                time.sleep(0.5)

                # SHT31 address 0x44(68)
                # read data back from 0x00(00), 6 bytes
                # Temp MSB, temp LSB, temp CRC, humidity MSB,
                #     humidity LSB, humidity CRC
                data = bus.read_i2c_block_data(i2c_address, 0x00, 6)

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
                    util.API_TEMP_FIELD: statistics.mean(cTemp_lst),
                    'Temp(C) std': statistics.pstdev(cTemp_lst),
                    'Temp(F) mean': statistics.mean(fTemp_lst),
                    'Temp(F) std': statistics.pstdev(fTemp_lst),
                    util.API_HUMIDITY_FIELD: statistics.mean(humidity_lst),
                    'Humidity(%RH) std': statistics.pstdev(humidity_lst),
                    }
        finally:
            # close the smbus connection
            bus.close()
            GPIO.cleanup()  # clean up GPIO


class Controller(Resource):
    def __init__(self):
        pass

    def get(self):
        helper = Sensors()
        return helper.get()


api.add_resource(Controller, "/")

if __name__ == "__main__":
    # launch the Flask API
    app.run(debug=True, host='0.0.0.0')
