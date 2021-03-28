import errno
import pathlib

from SiteMonitor import SiteMonitor
from Keymap import KeyStr

import sys, os, time, random
from reprint import output
from time import sleep
import threading
import traceback
import json

debug = False


def alert(monitor):
    pass


def col(string, c):
    colors = {
        "header": '\033[95m',
        "blue": '\033[94m',
        "green": '\033[92m',
        "yellow": '\033[93m',
        "red": '\033[91m',
        "bold": '\033[1m',
        "cyan": '\033[96m',
        "underline": '\033[4m',
        "ENDC": '\033[0m',
    }
    return colors[c] + string + colors["ENDC"]


def main():
    thisdir = str(pathlib.Path(__file__).parent.absolute())
    logdirs = [thisdir+d for d in ["/scrn/error/", "/log/"]]
    for d in logdirs:
        if not os.path.exists(os.path.dirname(d)):
            try:
                os.makedirs(os.path.dirname(d))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
    checkout_info = {}
    budget = {}
    monitor_url = {}
    debug = False
    headless = True
    if "--debug" in sys.argv:
        debug = True
    if "--gui" in sys.argv:
        headless = False

    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            cfg = json.load(f)
            checkout_info = cfg['checkout_info']
            budget = cfg['budget']

    if os.path.exists("urls.json"):
        with open("urls.json", "r") as f:
            monitor_url = json.load(f)

    urlc = 0

    with output(output_type="dict", interval=50) as output_lines:
        monitors = []
        for site in monitor_url:
            output_lines[site] = "starting monitor...."
            monitors.append(SiteMonitor(headless, monitor_url[site], auto_buy=not debug, debug=debug, budget=budget,
                                        checkout=checkout_info))
            for p in monitor_url[site]:
                urlc += len(monitor_url[site][p])

    for monitor in monitors:
        monitor.start()

    try:
        stoppedc = 0
        if not debug:
            with output(initial_len=urlc + 1, interval=50) as output_lines:
                output_lines[
                    0] = f"Monitor\t\t\t\t|\t\tProduct\t\t|\t\tPrice|\t\tStatus\t\t|\t\tInfo|Error\t\t|Threads:{threading.activeCount()}"
                while stoppedc < len(monitors):
                    i = 1
                    for m in monitors:
                        for u in m.URL:
                            instock = col("IN STOCK", "green") if m.URL[u]['status'] else col("OUT OF STOCK", "red")
                            instock = col("!!!! PURCHASE INITIATED !!!!", "cyan") if m.purchasing == u and m.URL[u][
                                'status'] else instock
                            output_lines[i] = "{}\t|\t\t{}\t\t|\t\t{}\t\t|\t{}\t|{}|{}".format(
                                m.domain,
                                col(m.URL[u]['prod'], "bold"),
                                col(m.URL[u]['price'], "cyan" if m.price_check(u) else "yellow"),
                                instock,
                                col(m.URL[u]['info'], "yellow"),
                                col(m.URL[u]['exc'], "red")
                            )
                            if m.URL[u]['status']:
                                alert(m)
                            i += 1
                        if m.stopped: stoppedc += 1
                    monitors = [m for m in monitors if not m.stopped]
        else:
            while stoppedc < len(monitors):
                stoppedc = 0
                for i, m in enumerate(monitors):
                    if m.stopped: stoppedc += 1
    except KeyboardInterrupt:
        print("Killing all monitors")
        for m in monitors:
            m.kill()
    except Exception as e:
        traceback.print_exc()
        print("Killing all monitors")
        print(os.system(f"taskkill /F /IM Firefox.exe"))
        for m in monitors:
            m.kill()
        exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
