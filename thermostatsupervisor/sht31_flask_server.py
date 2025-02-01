""""
flask API for raspberry pi
example from http://www.pibits.net/code/raspberry-pi-sht31-sensor-example.php
"""

# built-in imports
import re
import statistics
import subprocess
import sys
import time
import traceback

# raspberry pi libraries
try:
    from RPi import GPIO  # noqa F405 raspberry pi GPIO library
    import smbus2  # noqa F405

    pi_library_exception = None  # successful
except ImportError as ex:
    # hardware-related library, not needed in unittest mode
    print(traceback.format_exc())
    print(
        "WARNING: RPi or smbus library import error, "
        "this is expected in unittest mode"
    )
    pi_library_exception = ex  # unsuccessful

# third party imports
from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restful import Resource, Api  # noqa F405
from flask_wtf.csrf import CSRFProtect
import munch
from str2bool import str2bool

# local imports
from thermostatsupervisor import environment as env
from thermostatsupervisor import flask_generic as flg
from thermostatsupervisor import sht31_config
from thermostatsupervisor import utilities as util

# runtime override fields
input_flds = munch.Munch()
input_flds.debug_fld = "debug"

uip = None  # user inputs object

# SHT31D write commands (register, [data])
# spec: https://cdn-shop.adafruit.com/product-files/
# 2857/Sensirion_Humidity_SHT3x_Datasheet_digital-767294.pdf

# single shot mode: clock_stretching, repeatability
cs_enabled_high = (0x2C, [0x06])
cs_enabled_med = (0x2C, [0x0D])
cs_enabled_low = (0x2C, [0x10])
cs_disabled_high = (0x24, [0x00])
cs_disabled_med = (0x24, [0x0B])
cs_disabled_low = (0x24, [0x16])

# periodic data acquisition modes: mps, repeatability
mps_0p5_high = (0x20, [0x32])
mps_0p5_med = (0x20, [0x24])
mps_0p5_low = (0x20, [0x2F])
mps_1_high = (0x21, [0x30])
mps_1_med = (0x21, [0x26])
mps_1_low = (0x21, [0x2D])
mps_2_high = (0x22, [0x36])
mps_2_med = (0x22, [0x20])
mps_2_low = (0x22, [0x2B])
mps_4_high = (0x23, [0x34])
mps_4_med = (0x23, [0x22])
mps_4_low = (0x23, [0x29])
mps_10_high = (0x27, [0x37])
mps_10_med = (0x27, [0x21])
mps_10_low = (0x27, [0x2A])

# misc commands
fetch_data = (0xE0, [0x00])
period_meas_with_art = (0x2B, [0x32])
break_periodic_data = (0x30, [0x93])
soft_reset = (0x30, [0xA2])
reset = (0x00, [0x06])
enable_heater = (0x30, [0x6D])
disable_heater = (0x30, [0x66])
clear_status_register = (0x30, [0x41])
read_status_register = (0xF3, [0x2D])


class Sensors:
    """Sensor data."""

    def __init__(self):
        # set debug flag
        self.verbose = app.debug

    def convert_data(self, data):
        """
        Convert data from bits to real units.

        inputs:
            data(class 'list'): raw data structure
        returns:
            temp(int): raw temp data in bits.
            temp_c(float): temp on °C
            temp_f(float): temp in °F
            humidity(float): humidity in %RH
        """
        # convert the data
        temp = data[0] * 256 + data[1]
        temp_c = -45 + (175 * temp / 65535.0)
        temp_f = -49 + (315 * temp / 65535.0)
        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
        return temp, temp_c, temp_f, humidity

    def pack_data_structure(self, temp_f_lst, temp_c_lst, humidity_lst, rssi_lst):
        """
        Calculate statistics and pack data structure.

        inputs:
            temp_f_lst(list): list of fehrenheit measurements
            temp_c_lst(list): list of celcius measurements
            humidity_lst(list): list of humidity measurements
            rssi_lst(list): list of wifi rssi measurements
        returns:
            (dict): data structure.
        """
        return {
            sht31_config.API_MEASUREMENT_CNT: len(temp_f_lst),
            sht31_config.API_TEMPC_MEAN: statistics.mean(temp_c_lst),
            sht31_config.API_TEMPC_STD: statistics.pstdev(temp_c_lst),
            sht31_config.API_TEMPF_MEAN: statistics.mean(temp_f_lst),
            sht31_config.API_TEMPF_STD: statistics.pstdev(temp_f_lst),
            sht31_config.API_HUMIDITY_MEAN: statistics.mean(humidity_lst),
            sht31_config.API_HUMIDITY_STD: statistics.pstdev(humidity_lst),
            sht31_config.API_RSSI_MEAN: statistics.mean(rssi_lst),
            sht31_config.API_RSSI_STD: statistics.pstdev(rssi_lst),
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
        except OSError as exc:
            print(
                f"FATAL ERROR({util.get_function_name()}): i2c device at "
                f"address {hex(i2c_addr)} is not responding"
            )
            raise exc
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
            response = bus.read_i2c_block_data(i2c_addr, register, length)
        except OSError as exc:
            print(
                f"FATAL ERROR({util.get_function_name()}): i2c device at "
                f"address {hex(i2c_addr)} is not responding"
            )
            raise exc
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
            date_val = data[0] * 256 + data[1]
            resp = {
                "raw": data,
                "raw_binary": format(date_val, "#018b")[2:],
                "alert pending status(0=0,1=1+)": (date_val >> 15) & 1,
                # bit 15: 0=None, 1=at least 1 pending alert
                "heater status(0=off,1=on)": (date_val >> 13) & 1,
                # bit 13: 0=off, 1=on
                "RH tracking alert(0=no,1=yes)": (date_val >> 11) & 1,
                # bit 11: 0=no, 1=yes
                "T tracking alert(0=no,1=yes)": (date_val >> 10) & 1,
                # bit 10: 0=no, 1=yes
                "System reset detected(0=no,1=yes)": (date_val >> 4) & 1,
                # bit 4
                # 0=no reset since last clear cmd, 1=hard, soft, or supply fail
                "Command status(0=correct,1=failed)": (date_val >> 1) & 1,
                # bit 1: 0=successful, 1=invalid or field checksum
                "Write data checksum status(0=correct,1=failed)": (date_val >> 0) & 1,
                # bit 0: 0=correct, 1=failed
            }
        except IndexError:
            # parsing error, just return raw data
            print(
                "WARNING: fault register parsing error, just returning "
                "raw fault register data"
            )
            resp = {"raw": data}
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
        measurements = request.args.get(
            "measurements", sht31_config.MEASUREMENTS, type=int
        )
        seed = request.args.get("seed", sht31_config.UNIT_TEST_SEED, type=int)

        # data structure
        temp_f_lst = []
        temp_c_lst = []
        humidity_lst = []
        rssi_lst = []

        # loop for n measurements
        for measurement in range(measurements):
            # fabricated data for unit testing
            data = [seed + measurement % 2] * 5  # almost mid range

            # convert the data
            _, temp_c, temp_f, humidity = self.convert_data(data)
            rssi = self.get_iwconfig_wifi_strength()

            # add data to structure
            temp_f_lst.append(temp_f)
            temp_c_lst.append(temp_c)
            humidity_lst.append(humidity)
            rssi_lst.append(rssi)

        # return data on API
        return self.pack_data_structure(temp_f_lst, temp_c_lst, humidity_lst, rssi_lst)

    def get(self):
        """
        Get sensor data at ip:port.

        inputs:
            None
        returns:
            (dict): thermal data dictionary.
        """
        # get runtime parameters
        measurements = request.args.get("measurements", 1, type=int)

        # set address pin on SHT31
        self.set_sht31_address(
            sht31_config.I2C_ADDRESS, sht31_config.ADDR_PIN, sht31_config.ALERT_PIN
        )

        # activate smbus
        bus = smbus2.SMBus(sht31_config.I2C_BUS)
        time.sleep(0.5)

        # data structure
        temp_f_lst = []
        temp_c_lst = []
        humidity_lst = []
        rssi_lst = []

        try:
            # loop for n measurements
            for _ in range(measurements):
                # send single shot read command
                self.send_i2c_cmd(bus, sht31_config.I2C_ADDRESS, cs_enabled_high)

                # read the measurement data
                data = self.read_i2c_data(
                    bus, sht31_config.I2C_ADDRESS, register=0x00, length=0x06
                )

                # convert the data
                _, temp_c, temp_f, humidity = self.convert_data(data)
                rssi = self.get_iwconfig_wifi_strength()

                # add data to structure
                temp_f_lst.append(temp_f)
                temp_c_lst.append(temp_c)
                humidity_lst.append(humidity)
                rssi_lst.append(rssi)

            # return data on API
            return self.pack_data_structure(
                temp_f_lst, temp_c_lst, humidity_lst, rssi_lst
            )
        finally:
            # close the smbus connection
            bus.close()
            GPIO.cleanup()  # clean up GPIO

    def send_cmd_get_diag(self, i2c_command):
        """
        Send i2c command and read status register.

        inputs:
            i2c_command(int): i2c command to send
        returns:
            (dict): parsed fault register data.
        """
        # set address pin on SHT31
        self.set_sht31_address(
            sht31_config.I2C_ADDRESS, sht31_config.ADDR_PIN, sht31_config.ALERT_PIN
        )

        # activate smbus
        bus = smbus2.SMBus(sht31_config.I2C_BUS)
        time.sleep(0.5)

        try:
            # send single shot command
            self.send_i2c_cmd(bus, sht31_config.I2C_ADDRESS, i2c_command)

            # small delay
            time.sleep(1.0)

            # read the measurement data, 2 bytes data, 1 byte checksum
            data = self.read_i2c_data(
                bus, sht31_config.I2C_ADDRESS, register=0x00, length=0x03
            )

            # parse data into registers
            parsed_data = self.parse_fault_register_data(data)
            return parsed_data
        finally:
            # close the smbus connection
            bus.close()
            GPIO.cleanup()  # clean up GPIO

    def i2c_recovery(self):
        """
        Send 10 clock cycles on SCL IO pin to clear locked i2c bus.

        inputs:
             None
        returns:
            (dict): status message
        """
        addr_pin = sht31_config.SCL_PIN
        num_clock_cycles = 10
        recovery_freq_hz = 100000  # 100 KHz
        recovery_delay_sec = 1.0 / (2.0 * recovery_freq_hz)

        try:
            # set SCL pin for output
            GPIO.setmode(GPIO.BCM)  # broadcom pin numbering
            GPIO.setup(addr_pin, GPIO.OUT)  # address pin set as output

            # set pin high to start
            GPIO.output(addr_pin, GPIO.HIGH)

            # send clock cycles
            for _ in range(num_clock_cycles):
                time.sleep(recovery_delay_sec)
                GPIO.output(addr_pin, GPIO.LOW)
                time.sleep(recovery_delay_sec)
                GPIO.output(addr_pin, GPIO.HIGH)
            # status message
            msg_dict = {}
            msg_dict["action_complete"] = (
                f"{num_clock_cycles} SCL clock "
                f"toggles completed at "
                f"{recovery_freq_hz} Hz"
            )
            msg_dict["next_step"] = (
                "please reboot pi, restart flask server, and test bus using the diag "
                "command.  Reboot sequence may need to be repeated multiple times to "
                "resolve a locked i2c bus."
            )
            return {"i2c_recovery": msg_dict}
        finally:
            GPIO.cleanup()  # clean up GPIO

    def i2c_detect(self, bus=sht31_config.I2C_BUS):
        """
        Detect i2c device on bus.

        inputs:
             bus(int): i2c bus number
        returns:
            (dict): parsed device dictionary.
        """
        # send command
        with subprocess.Popen(
            ["sudo", "i2cdetect", "-y", str(bus)],
            stdout=subprocess.PIPE,
        ) as p:
            # cmdout = str(p.communicate())

            # read in raw data
            parsed_device_dict = {"i2c_detect": {}}
            bus_dict = {}
            for _ in range(0, 9):
                line = str(p.stdout.readline())
                addr_base = line[2:4]
                addr_payload = line[5:]

                # catch error condition
                if "Error" in line:
                    bus_dict["i2c_detect"]["error"] = line
                else:
                    # find devices on bus
                    device = 0
                    device_dict = {}
                    for match in re.finditer("[0-9][0-9]", addr_payload):
                        if match:
                            device_addr = match.group(0)
                            print(match.group(0))
                            device_dict["dev_" + str(device) + "_addr"] = str(
                                device_addr
                            )
                            bus_dict["addr_base_" + str(addr_base)] = device_dict
                            device += 1

        parsed_device_dict["i2c_detect"]["bus_" + str(bus)] = bus_dict
        return parsed_device_dict

    def get_iwlist_wifi_strength(self, cell=0) -> float:  # noqa R0201
        """
        Return the Raspberry pi wifi signal strength in dBm from iwlist.

        Code from iancoleman/python-iwlist used.

        inputs:
            cell(int): cell number to return.
        returns:
            (float): wifi signal strength in dBm.
        """
        if env.is_windows_environment():
            raise EnvironmentError(
                f"ERROR: {util.get_function_name()} is only supported on Linux"
            )

        cell_number_re = re.compile(
            r"^Cell\s+(?P<cellnumber>.+)\s+-\s+Address:" r"\s(?P<mac>.+)$"
        )
        regexps = [
            re.compile(r"^ESSID:\"(?P<essid>.*)\"$"),
            re.compile(r"^Protocol:(?P<protocol>.+)$"),
            re.compile(r"^Mode:(?P<mode>.+)$"),
            re.compile(
                r"^Frequency:(?P<frequency>[\d.]+) "
                r"(?P<frequency_units>.+) \(Channel "
                r"(?P<channel>\d+)\)$"
            ),
            re.compile(r"^Encryption key:(?P<encryption>.+)$"),
            re.compile(
                r"^Quality=(?P<signal_quality>\d+)/(?P<signal_total>\d+)"
                r"\s+Signal level=(?P<signal_level_dBm>.+) d.+$"
            ),
            re.compile(
                r"^Signal level=(?P<signal_quality>\d+)/" r"(?P<signal_total>\d+).*$"
            ),
        ]

        # Detect encryption type
        wpa_re = re.compile(r"IE:\ WPA\ Version\ 1$")
        wpa2_re = re.compile(r"IE:\ IEEE\ 802\.11i/WPA2\ Version\ 1$")

        # Parses the response from the command "iwlist scan"
        def parse(content):
            cells = []
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                cell_number = cell_number_re.search(line)
                if cell_number is not None:
                    cells.append(cell_number.groupdict())
                    continue
                wpa = wpa_re.search(line)
                if wpa is not None:
                    cells[-1].update({"encryption": "wpa"})
                wpa2 = wpa2_re.search(line)
                if wpa2 is not None:
                    cells[-1].update({"encryption": "wpa2"})
                for expression in regexps:
                    result = expression.search(line)
                    if result is not None:
                        if "encryption" in result.groupdict():
                            if result.groupdict()["encryption"] == "on":
                                cells[-1].update({"encryption": "wep"})
                            else:
                                cells[-1].update({"encryption": "off"})
                        else:
                            cells[-1].update(result.groupdict())
                        continue
            return cells

        # call iwlist terminal command
        # Runs the comnmand to scan the list of networks.
        # Must run as super user.
        # Does not specify a particular device, so will scan all
        # network devices.
        scan_result = self.shell_cmd(["iwlist", "wlan0", "scan"])
        if self.verbose:
            print(f"iwlist scan results: {scan_result}")

        # parse out the RSSI result
        parse_result = parse(scan_result)
        if self.verbose:
            print(f"iwlist parse results: {parse_result}")

        return float(parse_result[cell]["signal_level_dBm"])

    def get_iwconfig_wifi_strength(self) -> float:  # noqa R0201
        """
        Return the Raspberry pi wifi signal strength in dBm from iwconfig.

        inputs:
            None.
        returns:
            (float): wifi signal strength in dBm.
        """
        regexps_iwconfig = [
            re.compile(r"^ESSID:\"(?P<essid>.*)\"$"),
            re.compile(
                r"^Frequency:(?P<frequency>[\d.]+) "
                r"(?P<frequency_units>.+)\s+ "
                r"Access Point:\"(?P<mac_addr>.*)\"$"
            ),
            re.compile(
                r"^Link Quality=(?P<signal_quality>\d+)/"
                r"(?P<signal_total>\d+)"
                r"\s+Signal level=(?P<signal_level_dBm>.+) d.+$"
            ),
        ]

        regexps_netsh = [
            re.compile(r"^\s*SSID\s*:\s(?P<essid>.*)\s*"),
            re.compile(r"^\s*Channel\s*:(?P<frequency>[\d.])\s*"),
            re.compile(r"^\s*BSSID\s*:\s(?P<mac_addr>.*)\s*"),
            re.compile(r"^\s*Signal\s*:\s(?P<signal_quality>.*)%\s*"),
        ]

        # Parses the response from the command "iwconfig"
        def parse(content, regexps):
            parse_result = {}
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                for expression in regexps:
                    result = expression.search(line)
                    if result is not None:
                        parse_result.update(result.groupdict())
            return parse_result

        # call iwconfig terminal command
        if env.is_windows_environment():
            scan_cmd = "netsh"
            scan_result = self.shell_cmd([scan_cmd, "wlan", "show", "interfaces"])
        else:  # assume Linux
            scan_cmd = "iwconfig"
            scan_result = self.shell_cmd([scan_cmd])
        if self.verbose:
            print(f"{scan_cmd} scan results: {scan_result}")

        # parse out the RSSI result
        if env.is_windows_environment():
            parse_result = parse(scan_result, regexps_netsh)
            # add calculation for dBm = quality / 2 - 100
            parse_result.update(
                {"signal_level_dBm": int(parse_result["signal_quality"]) / 2 - 100}
            )
        else:  # assume Linux
            parse_result = parse(scan_result, regexps_iwconfig)
        if self.verbose:
            print(f"{scan_cmd} parse results: {parse_result}")

        return float(parse_result["signal_level_dBm"])

    def shell_cmd(self, cmd_lst):
        """
        Send a shell command to the terminal and return results.

        inputs:
            cmd_lst(list):  list of one or more commands / parameters.
        returns:
            (str): result.
        """
        with subprocess.Popen(
            cmd_lst, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc:
            result = proc.stdout.read().decode("utf-8")
        return result


class Controller(Resource):
    """Production controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.get()


class ControllerUnit(Resource):
    """Unit test Controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.get_unit_test()


class ReadFaultRegister(Resource):
    """Diagnostic Controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(read_status_register)


class ClearFaultRegister(Resource):
    """Clear Diagnostic Controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(clear_status_register)


class EnableHeater(Resource):
    """Enable heater Controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(enable_heater)


class DisableHeater(Resource):
    """Disable heater Controller."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(disable_heater)


class SoftReset(Resource):
    """i2C soft reset."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(soft_reset)


class Reset(Resource):
    """i2C hard reset."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.send_cmd_get_diag(reset)


class I2CRecovery(Resource):
    """Issue i2c recovery sequence."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.i2c_recovery()


class I2CDetect(Resource):
    """Issue i2c detect on default bus."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.i2c_detect()


class I2CDetectBus0(Resource):
    """Issue i2c detect on bus 0."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.i2c_detect(0)


class I2CDetectBus1(Resource):
    """Issue i2c detect on bus 1."""

    def __init__(self):
        pass

    # @limiter.limit(fast_rate_limiter)
    def get(self):
        """Map the get method."""
        helper = Sensors()
        return helper.i2c_detect(1)


fast_rate_limiter = ["200 per day", "1 per hour"]


def create_app():
    """Create the api object."""
    app_ = Flask(__name__)

    # add API routes
    api = Api(app_)

    # Initialize rate limiter
    limiter = Limiter(
        get_remote_address,
        app=app_,
        default_limits=fast_rate_limiter
    )

    # add API functions
    api.add_resource(Controller, "/")
    api.add_resource(ControllerUnit, sht31_config.flask_folder.unit_test)
    api.add_resource(ReadFaultRegister, sht31_config.flask_folder.diag)
    api.add_resource(ClearFaultRegister, sht31_config.flask_folder.clear_diag)
    api.add_resource(EnableHeater, sht31_config.flask_folder.enable_heater)
    api.add_resource(DisableHeater, sht31_config.flask_folder.disable_heater)
    api.add_resource(SoftReset, sht31_config.flask_folder.soft_reset)
    api.add_resource(Reset, sht31_config.flask_folder.reset)
    api.add_resource(I2CRecovery, sht31_config.flask_folder.i2c_recovery)
    api.add_resource(I2CDetect, sht31_config.flask_folder.i2c_detect)
    api.add_resource(I2CDetectBus0, sht31_config.flask_folder.i2c_detect_0)
    api.add_resource(I2CDetectBus1, sht31_config.flask_folder.i2c_detect_1)

    return app_


# create the flask app
app = create_app()
csrf = CSRFProtect(app)  # enable CSRF protection
ip_ban = flg.initialize_ipban(app)  # hacker blacklisting agent
flg.set_flask_cookie_config(app)
flg.print_flask_config(app)


@app.route("/favicon.ico")
def favicon():
    """Set favicon for browser tab."""
    return app.send_static_file("sht31.ico")


class UserInputs(util.UserInputs):
    """Manage runtime arguments for sht31_flask_server."""

    def __init__(self, argv_list=None, help_description=None, suppress_warnings=False):
        """
        UserInputs constructor for sht31_flask_server.

        inputs:
            argv_list(list): override runtime values.
            help_description(str): description field for help text.
            suppress_warnings(bool): True to suppress warning msgs.
        """
        self.argv_list = argv_list
        self.help_description = help_description
        self.suppress_warnings = suppress_warnings

        # initialize parent class
        super().__init__(argv_list, help_description, suppress_warnings)

    def initialize_user_inputs(self, parent_keys=None):
        """
        Populate user_inputs dict.
        """
        if parent_keys is None:
            parent_keys = [self.default_parent_key]
        self.valid_sflags = []
        # define the user_inputs dict.
        for parent_key in parent_keys:
            self.user_inputs = {
                parent_key: {
                    input_flds.debug_fld: {
                        "order": 1,  # index in the argv list
                        "value": None,
                        "type": lambda x: bool(str2bool(str(x).strip())),
                        "default": False,
                        "valid_range": [True, False, 1, 0],
                        "sflag": "-d",
                        "lflag": "--" + input_flds.debug_fld,
                        "help": "flask server debug mode",
                        "required": False,
                    },
                },
            }
            self.valid_sflags += [
                self.user_inputs[parent_key][k]["sflag"]
                for k in self.user_inputs[parent_key].keys()
            ]


if __name__ == "__main__":
    print("SHT31 sensor Flask server")

    # enable logging to STDERR for Flask
    util.log_stdout_to_stderr = True

    # verify environment
    env.get_python_version()
    if not env.is_raspberrypi_environment(True):
        raise EnvironmentError(
            "ERROR: SHT31 Flask server only supported on Raspberry PI environment"
        )

    # parse runtime parameters
    uip = UserInputs()
    debug = uip.get_user_inputs(uip.default_parent_key, "debug")
    print(f"Flask debug mode={debug}", file=sys.stderr)

    # launch the Flask API on development server
    flg.schedule_ipban_block_list_report(ip_ban, debug_mode=debug)
    app.run(
        host="0.0.0.0",
        port=sht31_config.FLASK_PORT,
        debug=debug,
        threaded=True,  # threaded=True may speed up rendering on web page
        ssl_context=sht31_config.FLASK_SSL_CERT,
    )
