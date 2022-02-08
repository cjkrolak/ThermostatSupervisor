"""
SHT31 config file.
"""
import bunch

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
flask_folder = bunch.Bunch()
flask_folder.production = ""
flask_folder.unit_test = "/unit"
flask_folder.diag = "/diag"
flask_folder.clear_diag = "/clear_diag"
flask_folder.enable_heater = "/enable_heater"
flask_folder.disable_heater = "/disable_heater"
flask_folder.soft_reset = "/soft_reset"
flask_folder.reset = "/reset"

# SHT31 API field names
API_MEASUREMENT_CNT = 'measurements'
API_TEMPC_MEAN = 'Temp(C) mean'
API_TEMPC_STD = 'Temp(C) std'
API_TEMPF_MEAN = 'Temp(F) mean'
API_TEMPF_STD = 'Temp(F) std'
API_HUMIDITY_MEAN = 'Humidity(%RH) mean'
API_HUMIDITY_STD = 'Humidity(%RH) std'

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
                     "zones": [0, 1, UNIT_TEST_ZONE],
                     "modes": ["OFF_MODE"]}

sht31_metadata = {
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

# SHT31D config
I2C_ADDRESS = 0x45  # i2c address b
MEASUREMENTS = 10  # number of MEASUREMENTS to average

# pi0 config
ALERT_PIN = 17  # yellow wire, GPIO17 (pi pin 11)
ADDR_PIN = 4  # white wire, GPIO4, low = 0x44, high=0x45 (pi pin 7)
