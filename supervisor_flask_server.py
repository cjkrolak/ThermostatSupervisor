"""
Flask server for displaying supervisor output on web page.
"""
# built-in libraries
from flask import Flask, Response
import html
from subprocess import Popen, PIPE, STDOUT, DEVNULL
import sys
import webbrowser

# local imports
import supervise as sup
import thermostat_api as api

# flask server
flask_ip_address = '127.0.0.1'
flask_port = 80
flask_url = 'http://' + flask_ip_address + ':' + str(flask_port)

argv = []  # supervisor runtime args list


def create_app():

    app_ = Flask(__name__)
    # api = Api(app)

    # api.add_resource(Controller, "/")
    return app_


# create the flask app
app = create_app()


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
    webbrowser.open(flask_url, 2)
    app.run(host=flask_ip_address, port=flask_port,
            debug=False,  # True causes 2 tabs to open, enables auto-reload
            threaded=True)  # threaded=True may speed up rendering on web page
