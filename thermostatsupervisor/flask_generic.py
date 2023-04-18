"""Generic Flask functionality."""

# built-in libraries
import datetime

# third party libraries
from flask_apscheduler import APScheduler
from flask_ipban import IpBan

# local imports

# ipban
ipban_ban_count = 1
ipban_ban_seconds = 3600 * 24 * 7  # 1 wk
ipban_persistent = False  # True to persist across restarts


def initialize_ipban(app):
    """
    Initialize ipban agent for blocking hacking attempts.

    inputs:
        app (flask app object)
    returns:
        (ip_ban object)
    """
    # setup ipban
    ip_ban = IpBan(app=app,
                   ban_count=ipban_ban_count,
                   ban_seconds=ipban_ban_seconds,
                   persist=ipban_persistent)
    ip_ban.init_app(app)
    ip_ban.load_nuisances()
    print_ipban_block_list(ip_ban)
    return ip_ban


def print_ipban_block_list(ip_ban):
    """
    Print the current ip_ban block list to the console.

    inputs:
        ip_ban(ip_ban object)
    returns:
        None
    """
    # s = ""
    # s += "<table class='table'><thead>\n"
    # s += ("<tr><th>ip</th><th>count</th><th>permanent</th><th>url</th><th>"
    #       f"timestamp</th></tr>\n")
    # s += ""</thead><tbody>\n"
    # for k, r in ip_ban.get_block_list().items():
    #     s += (f"<tr><td>{k}</td><td>{r['count']}</td><td>"
    #           f"{r.get('permanent', '')}</td><td>{r.get('url', '')}</td><td>"
    #           f"{r['timestamp']}</td></tr>\n")
    # print(f"{s}")
    print(f"ip_ban black list: {ip_ban.get_block_list()}")


def print_ipban_block_list_with_timestamp(ip_ban):
    """
    Print the current ip_ban block list to the console with timestamp.

    inputs:
        ip_ban(ip_ban object)
    returns:
        None
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{now_str}: ip_ban black list: {ip_ban.get_block_list()}")


def schedule_ipban_block_list_report(ip_ban, debug_mode=False):
    """
    Schedule an ip_ban blocked ip list report.

    inputs:
        ip_ban(ip_ban object)
    returns:
        None
    """
    # interval = 1 day std, 1 min in debug mode
    interval_sec = 60 * [60 * 24, 1][debug_mode]
    print(f"ip_ban blacklist report scheduled every {interval_sec / 60.0} "
          "minutes")
    scheduler = APScheduler()
    kwargs = {"ip_ban": ip_ban}
    scheduler.add_job(id='ip_ban blacklist report',
                      func=print_ipban_block_list_with_timestamp,
                      kwargs=kwargs,
                      trigger="interval", seconds=interval_sec)
    scheduler.start()


def set_flask_cookie_config(app):
    """
    Set cookie config to protect against cookie attack vectors in
    the Flask configuration.

    inputs:
        app (flask app object)
    returns:
        None
    """
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )


def print_flask_config(app):
    """
    """
    print("flask config:")
    print(f"{app.config}")
