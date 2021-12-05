"""
Flask server for displaying supervisor output on web page.
"""
# built-in libraries
from flask import Flask, Response, send_from_directory
from flask_wtf.csrf import CSRFProtect
import html
import os
from subprocess import Popen, PIPE, STDOUT, DEVNULL
import sys
import webbrowser

# local imports
import supervise as sup
import thermostat_api as api
import utilities as util

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
flask_port = 5080  # note: ports below 1024 require root access on Linux
flask_url = 'http://' + flask_ip_address + ':' + str(flask_port)

argv = []  # supervisor runtime args list


def create_app():

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
    return send_from_directory(os.path.join(app.root_path, 'image'),
                               'honeywell.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/')
def index():
    def run_supervise():
        sup.argv = argv  # pass runtime overrides to supervise
        print("DEBUG: in run_supervise, argv=%s" % argv)
        user_inputs = api.parse_all_runtime_parameters(argv)
        print("DEBUG: in run_supervise, user_inputs=%s" %
              user_inputs)
        thermostat_type = user_inputs["thermostat_type"]
        zone = user_inputs["zone"]
        measurements = user_inputs["measurements"]
        title = ("%s thermostat zone %s, %s measurements" %
                 (thermostat_type, zone, measurements))
        yield "<!doctype html><title>%s</title>" % title

        # runtime variabless
        executable = "python"
        script = "supervise.py"
        if argv:
            # argv list override for unit testing
            arg_list = [executable, script] + argv[1:]
        elif len(sys.argv) > 1:
            arg_list = [executable, script] + sys.argv[1:]
        else:
            arg_list = [executable, script]
        with Popen(arg_list, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT,
                   bufsize=1, universal_newlines=True, shell=True) as p:
            i = 0
            for line in p.stdout:
                print("DEBUG: line %s: %s" % (i, line), file=sys.stderr)
                i += 1
                yield "<code>{}</code>".format(html.escape(line.rstrip("\n")))
                yield "<br>\n"
    return Response(run_supervise(), mimetype='text/html')


if __name__ == '__main__':
    # show the page in browser
    webbrowser.open(flask_url, new=2)
    app.run(host=flask_ip_address, port=flask_port,
            debug=False,  # True causes 2 tabs to open, enables auto-reload
            threaded=True)  # threaded=True may speed up rendering on web page
