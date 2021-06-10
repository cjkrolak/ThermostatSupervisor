"""
Flask server for displaying supervisor output on web page.
"""
import html
from subprocess import Popen, PIPE, STDOUT, DEVNULL
import sys
import webbrowser

from flask import Flask, Response
app = Flask(__name__)

# port for viewing flask
flask_port = 5000


@app.route('/')
def index():
    def g():
        yield "<!doctype html><title>Stream subprocess output</title>"

        # runtime variables
        executable = "python"
        script = "supervise.py"
        if len(sys.argv) > 1:
            arg_list = [executable, script] + sys.argv[1:]
        else:
            arg_list = [executable, script]
        print("just before popen command")
        with Popen(arg_list, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT,
                   bufsize=1, universal_newlines=True, shell=True) as p:
            print("in popen command: %s" % type(p.stdout))
            i = 0
            for line in p.stdout:
                print("line %s" % i)
                i += 1
                yield "<code>{}</code>".format(html.escape(line.rstrip("\n")))
                yield "<br>\n"
    print("returning g")
    return Response(g(), mimetype='text/html')


if __name__ == '__main__':
    # show the page in browser
    webbrowser.open('http://127.0.0.1:' + str(flask_port))
    app.run(host='0.0.0.0', port=flask_port)
