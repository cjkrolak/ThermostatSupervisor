"""
Flask server for displaying supervisor output on web page.
"""
# built-in libraries
import html
import os
from subprocess import Popen, PIPE, STDOUT, DEVNULL
import sys
import webbrowser

# third party imports
from flask import Flask, Response, send_from_directory
from flask_wtf.csrf import CSRFProtect

# local imports
from thermostatsupervisor import supervise as sup
from thermostatsupervisor import thermostat_api as api
from thermostatsupervisor import utilities as util

# flask server
if util.is_windows_environment():
    # win server from Eclipse IDE:
    #     loopback will work to itself but not remote clients
    #     local IP works both itself and to remote Linux client.
    # win server from command line:
    #
    flask_ip_address = util.get_local_ip()
else:
    # Linux server from Thoney IDE: must update Thonny to run from root
    #   page opens on both loopback Linux and remote Win client, but
    #       no data loads.
    # flask_ip_address = '127.0.0.1'  # almost works from Linux client
    flask_ip_address = util.get_local_ip()  # almost works from Linux client
    # on Linux both methds are returning correct page header, but no data
FLASK_PORT = 5001  # note: ports below 1024 require root access on Linux
FLASK_USE_HTTPS = False  # HTTPS requires a cert to be installed.
if FLASK_USE_HTTPS:
    FLASK_SSL_CERT = 'adhoc'  # adhoc
    flask_kwargs = {'ssl_context': FLASK_SSL_CERT}
    FLASK_URL_PREFIX = "https://"
else:
    FLASK_SSL_CERT = None  # adhoc
    flask_kwargs = {}
    FLASK_URL_PREFIX = "http://"
flask_url = FLASK_URL_PREFIX + flask_ip_address + ':' + str(FLASK_PORT)

argv = []  # supervisor runtime args list


def create_app():
    """Create the flask object."""
    app_ = Flask(__name__)
    # api = Api(app)

    # api.add_resource(Controller, "/")
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
    """Faviocon displayed in browser tab."""
    return send_from_directory(os.path.join(app.root_path, 'image'),
                               'honeywell.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    """index route"""
    def run_supervise():
        sup.argv = argv  # pass runtime overrides to supervise
        util.parse_runtime_parameters(argv, api.user_inputs)
        thermostat_type = api.get_user_inputs(api.THERMOSTAT_TYPE_FLD)
        zone = api.get_user_inputs(api.ZONE_FLD)
        measurements = api.get_user_inputs(api.MEASUREMENTS_FLD)
        title = (f"{thermostat_type} thermostat zone {zone}, "
                 f"{measurements} measurements")
        yield f"<!doctype html><title>{title}</title>"

        # runtime variabless
        executable = "python"
        dont_buffer = "-u"
        script = "supervise.py"
        if argv:
            # argv list override for unit testing
            arg_list = [executable, dont_buffer, script] + argv[1:]
        elif len(sys.argv) > 1:
            arg_list = [executable, dont_buffer, script] + sys.argv[1:]
        else:
            arg_list = [executable, dont_buffer, script]
        with Popen(arg_list, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT,
                   bufsize=1, universal_newlines=True, shell=True) as p_out:
            for i, line in enumerate(p_out.stdout):
                print(f"DEBUG: line {i}: {line}", file=sys.stderr)
                yield "<code>{}</code>".format(html.escape(line.rstrip("\n")))
                yield "<br>\n"
    return Response(run_supervise(), mimetype='text/html')


if __name__ == '__main__':
    # show the page in browser
    webbrowser.open(flask_url, new=2)
    app.run(host=flask_ip_address,
            port=FLASK_PORT,
            debug=False,  # True causes 2 tabs to open, enables auto-reload
            threaded=True,  # threaded=True may speed up rendering on web page
            ssl_context=FLASK_SSL_CERT)
