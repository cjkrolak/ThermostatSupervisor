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
import thermostat_api as api

# flask server
app = Flask(__name__)
flask_ip_address = '127.0.0.1'
flask_port = 80
flask_url = 'http://' + flask_ip_address + ':' + str(flask_port)


@app.route('/')
def index():
    def run_supervise():
        user_inputs = api.parse_all_runtime_parameters()
        thermostat_type = user_inputs[0]
        zone = user_inputs[1]
        title = "%s thermostat zone %s" % (thermostat_type, zone)
        yield "<!doctype html><title>%s</title>" % title

        # runtime variables
        executable = "python"
        script = "supervise.py"
        if len(sys.argv) > 1:
            arg_list = [executable, script] + sys.argv[1:]
        else:
            arg_list = [executable, script]
        with Popen(arg_list, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT,
                   bufsize=1, universal_newlines=True, shell=True) as p:
            i = 0
            for line in p.stdout:
                print("DEBUG: line %s: %s" % (i, line))
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
