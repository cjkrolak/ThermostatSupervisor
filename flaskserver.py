"""
Flask server for posting supervisor status messages.
"""


from contextlib import redirect_stdout
import flask
import subprocess
import time
import webbrowser

# script to run
path = '/honeywell.py'
console_log_file = "honeywell_status.txt"

app = flask.Flask(__name__)


@app.route('/yield')
def index():
    def inner():
        proc = subprocess.Popen(
            (path,),
            shell=True,
            stdout=subprocess.PIPE
        )

        for line in iter(proc.stdout.readline, ''):
            print("console: " + line)
            time.sleep(10)  # Don't need this just shows the text streaming
            yield line.rstrip() + '<br/>\n'

    return flask.Response(inner(), mimetype='text/html')
    # text/html is required for most browsers to show th$


if __name__ == "__main__":

    # redirect console output to file for posting
    with open(console_log_file, 'w') as f:
        with redirect_stdout(f):
            print("it now prints to %s" % console_log_file)

    # show the page in browser
    webbrowser.open('http://localhost:23423')
    app.run(host='localhost', port=23423, debug=True)
