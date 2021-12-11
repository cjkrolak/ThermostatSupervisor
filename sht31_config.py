"""
SHT31 config file.
"""
ALIAS = "sht31"

# SHT31 thermometer zones
LOFT_SHT31 = 0  # zone 0, local IP 192.168.86.15
LOFT_SHT31_REMOTE = 1  # zone 1

# unit test parameters
UNIT_TEST_ZONE = 99
unit_test_seed = 0x7F
UNIT_TEST_ENV_KEY = "SHT31_REMOTE_IP_ADDRESS_" + str(UNIT_TEST_ZONE)
FLASK_UNIT_TEST_FOLDER = "/unit"

# diagnostic parameters
FLASK_DIAG_FOLDER = "/diag"
FLASK_CLEAR_DIAG_FOLDER = "/clear_diag"

# SHT31 API field names
API_MEASUREMENT_CNT = 'measurements'
API_TEMPC_MEAN = 'Temp(C) mean'
API_TEMPC_STD = 'Temp(C) std'
API_TEMPF_MEAN = 'Temp(F) mean'
API_TEMPF_STD = 'Temp(F) std'
API_HUMIDITY_MEAN = 'Humidity(%RH) mean'
API_HUMIDITY_STD = 'Humidity(%RH) std'

# all environment variables required by code should be registered here
env_variables = {
    "SHT31_REMOTE_IP_ADDRESS_0": None,
    "SHT31_REMOTE_IP_ADDRESS_1": None,
    UNIT_TEST_ENV_KEY: None,
    }

# min required env variables on all runs
required_env_variables = {
            "GMAIL_USERNAME": None,
            "GMAIL_PASSWORD": None,
            "SHT31_REMOTE_IP_ADDRESS_": None,  # prefix only, excludes zone
            }

# supported thermostat configs
supported_configs = {"module": "sht31",
                     "type": 3,
                     "zones": [0, 1, UNIT_TEST_ZONE],
                     "modes": ["OFF_MODE"]}

# SHT31D config
i2c_address = 0x45  # i2c address b
measurements = 10  # number of measurements to average

# pi0 config
alert_pin = 17  # yellow wire, GPIO17 (pi pin 11)
addr_pin = 4  # white wire, GPIO4, low = 0x44, high=0x45 (pi pin 7)
