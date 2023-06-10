"""
SHT31 config file.
"""
# built-in imports
import munch

# local imports
from thermostatsupervisor import utilities as util

ALIAS = "sht31"

# SHT31 thermometer zones
LOFT_SHT31 = 0  # zone 0, local IP 192.168.86.15
LOFT_SHT31_REMOTE = 1  # zone 1

# unit test parameters
UNIT_TEST_ZONE = 99
UNIT_TEST_SEED = 0x7F
UNIT_TEST_ENV_KEY = "SHT31_REMOTE_IP_ADDRESS_" + str(UNIT_TEST_ZONE)
FLASK_PORT = 5000  # note: ports below 1024 require root access on Linux
FLASK_USE_HTTPS = False  # HTTPS requires a cert to be installed.
FLASK_DEBUG_MODE = False  # True to enable flask debugging mode
if FLASK_USE_HTTPS:
    FLASK_SSL_CERT = 'adhoc'  # adhoc
    FLASK_KWARGS = {'ssl_context': FLASK_SSL_CERT}
    FLASK_URL_PREFIX = "https://"
else:
    FLASK_SSL_CERT = None  # adhoc
    FLASK_KWARGS = {}
    FLASK_URL_PREFIX = "http://"

# diagnostic parameters
flask_folder = munch.Munch()
flask_folder.production = ""
flask_folder.unit_test = "/unit"
flask_folder.diag = "/diag"
flask_folder.clear_diag = "/clear_diag"
flask_folder.enable_heater = "/enable_heater"
flask_folder.disable_heater = "/disable_heater"
flask_folder.soft_reset = "/soft_reset"
flask_folder.reset = "/reset"
flask_folder.i2c_recovery = "/i2c_recovery"
flask_folder.i2c_detect = "/i2c_detect"
flask_folder.i2c_detect_0 = "/i2c_detect/0"
flask_folder.i2c_detect_1 = "/i2c_detect/1"

# SHT31 API field names
API_MEASUREMENT_CNT = 'measurements'
API_TEMPC_MEAN = 'Temp(C) mean'
API_TEMPC_STD = 'Temp(C) std'
API_TEMPF_MEAN = 'Temp(F) mean'
API_TEMPF_STD = 'Temp(F) std'
API_HUMIDITY_MEAN = 'Humidity(%RH) mean'
API_HUMIDITY_STD = 'Humidity(%RH) std'

# SHT31D config
I2C_BUS = 1  # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
I2C_ADDRESS = 0x45  # i2c address, 0x44=a, 0x45=b
MEASUREMENTS = 10  # number of MEASUREMENTS to average

# pi0 / sht31 connection config, -1 means non-addressible pin
V3_PIN = -1  # 3.3v power pin (red), (pi pin 1)
SDA_PIN = 2  # i2c data signal (brown), GPIO2 (pi pin 3)
SCL_PIN = 3  # i2c clock signal (orange), GPIO3 (pi pin 5)
ADDR_PIN = 4  # i2c address (white), GPIO4, low = 0x44, high=0x45 (pi pin 7)
GND_PIN = -1  # ground wire (black), (pi pin 9)
ALERT_PIN = 17  # i2c alert pint (yellow), GPIO17 (pi pin 11)

# all environment variables specific to this thermostat type
env_variables = {
    "SHT31_REMOTE_IP_ADDRESS_0": None,
    "SHT31_REMOTE_IP_ADDRESS_1": None,
    UNIT_TEST_ENV_KEY: None,
}

# min required env variables on all runs
required_env_variables = {
    "SHT31_REMOTE_IP_ADDRESS_": None,  # prefix only, excludes zone
}

# supported thermostat configs
supported_configs = {"module": "sht31",
                     "type": 3,
                     "zones": [LOFT_SHT31, LOFT_SHT31_REMOTE, UNIT_TEST_ZONE],
                     "modes": ["OFF_MODE", "UNKNOWN_MODE"]}

# metadata dict:
# 'zone_name' is returned by self.get_zone_name()
# 'host_name' is used for DNS lookup to determine if device
# is on the current network.
metadata = {
    LOFT_SHT31: {"zone_name": "Loft (local)",
                 "host_name": "raspberrypi0.lan",
                 },
    LOFT_SHT31_REMOTE: {"zone_name": "loft (remote)",
                        "host_name": "none",
                        },
    UNIT_TEST_ZONE: {"zone_name": "unittest",
                     "host_name": "none",
                     },
}


def get_preferred_zone():
    """
    Return the preferred zone number.  For this thermostat the preferred zone
    number is the local zone if present, otherwise will fail over the the
    remote zone.

    inputs:
        None
    returns:
        (int): zone number.
    """
    # loopback does not work so use local sht31 zone if testing
    # on the local net.  If not, use the DNS name.
    local_host = metadata[LOFT_SHT31]["host_name"]
    zone = str([LOFT_SHT31_REMOTE, LOFT_SHT31][
        util.is_host_on_local_net(local_host, verbose=False)[0]])
    return zone


default_zone = get_preferred_zone()
default_zone_name = ALIAS + "_" + str(default_zone)

argv = [
    "supervise.py",  # module
    ALIAS,  # thermostat
    str(default_zone),  # zone
    "17",  # poll time in sec
    "357",  # reconnect time in sec
    "2",  # tolerance
    "OFF_MODE",  # thermostat mode
    "2",  # number of measurements
    ]
