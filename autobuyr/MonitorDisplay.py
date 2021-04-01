import os
import sys
import threading
import traceback

from reprint import output

from autobuyr.SiteMonitor import SiteMonitor


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


def statcol(string):
    lc = string.lower()
    if string == "running":
        return col(string, "green")
    elif "quit successfully" in string:
        return col(string, "red")
    else:
        return col(string, "yellow")


class MonitorDisplay:
    def __init__(self, monitors, spacing=20):
        self.monitors = monitors
        self.space = spacing
        self.stopped = False

    def sp(self, txt, char_count=None):
        if not char_count:
            char_count = self.space + (0 if '\033' not in txt else 8 if '[1m' in txt else 9)
        d = char_count - len(txt)
        return ''.join([" " for s in range(d)])

    def format_url(self, url):
        i = url[0]
        url = url[1]
        m = 20

        domain = url[0].split(".")[1]
        prod = col(url[1]['prod'], "bold")
        price = col(url[1]['price'], "cyan" if url[1]['in_budget'] else "yellow")
        instock = col("IN STOCK", "green") if url[1]['status'] else col("OUT OF STOCK", "red")
        instock = col("ATTEMPTING PURCHASE", "green") if url[1]['purchasing'] and url[1]['status'] else instock
        info = col(url[1]['info'], "yellow" if "purchased" not in url[1] else "blue")
        exc = col(url[1]['exc'][:self.space], "red")
        if "purchased" in url[1] and url[1]['prod'] == "test":
            exc = col(f"Test passed: {url[1]['te']}", "blue")
        ln = [prod, price, instock, info]
        output = f"{self.sp(str(i) + ':', len('_Monitor:'))}{domain} {self.sp(domain)}|\t\t" + ''.join(
            f"{i} {self.sp(i)}|\t\t" for i in ln) + f"{exc}"
        return output

    def run(self):
        columns = ["Vendor", "Products", "Price", "Status", "Info", "Error"]
        with output(output_type="dict", sort_key=lambda x: "_Status" not in x[0] or "_" not in x[0], interval=250) as output_lines:
            output_lines.clear()
            urls = []
            for m in self.monitors:
                urls.extend(list(map(lambda u: (u, m.URL[u]), m.URL)))
            while not self.stopped and len([m for m in self.monitors if not m.exited]) > 0:
                output_lines[col('_Monitor','header')] = ''.join(f"{c} {self.sp(c)}|\t\t" for c in columns)
                for i in range(500):
                    try:
                        for u in enumerate(urls, start=1):
                            output_lines[str(u[0])] = self.format_url(u)
                        output_lines[col('_Status_', 'header')] = "".join([f"{m.domain}:{statcol(m.STATUS)} |" for m in self.monitors])
                    except KeyboardInterrupt:
                        output_lines.append(col("Stopping Monitors!", "red"))
                        # output_lines['_Monitor'] = ''.join(f"{c} {self.sp(c)}|\t\t" for c in columns)
                        for m in self.monitors:
                            m.kill()
                    except:
                        output_lines.clear()
                        traceback.print_exc()
                        output_lines.append(col("Stopping Monitors!", "red"))
                        for m in self.monitors:
                            m.kill()
                output_lines.clear()
            output_lines.append(col("All monitors stopped. Exiting.", "yellow"))

    def reset(self):
        with output(interval=50) as output_lines:
            output_lines.clear()
            output_lines.append(col("Stopping Monitors!", "red"))

    def kill(self):
        self.stopped = True
