import os
import threading

from reprint import output

from SiteMonitor import SiteMonitor


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

class MonitorDisplay:
    def __init__(self, monitors):
        self.monitors = monitors
        self.stopped=False

    def show(self):
        urlc = sum([len(m.URL) for m in self.monitors])
        exitc=0
        with output(initial_len=urlc + 1, interval=50) as output_lines:
            output_lines[0] = f"Monitor\t\t\t\t|\t\tProduct\t\t|\t\tPrice|\t\tStatus\t\t|\t\tInfo|Error\t\t|Threads:{threading.activeCount()}"
            try:
                while exitc < len(monitors):
                    i = 1
                    monitors_alive = [m for m in monitors if not m.exited]
                    if len(monitors_alive) < len(monitors):
                        monitors = monitors_alive
                        ol = [output_lines[0]]
                        for m in monitors:
                            ol.append(["....." for u in m.URL])
                            if len(output_lines) > urlc + 1:
                                ol.append(output_lines[urlc + 1:])
                        output_lines.change(ol)
                    for m in monitors:

                        for u in m.URL:
                            instock = col("IN STOCK", "green") if m.URL[u]['status'] else col("OUT OF STOCK", "red")
                            instock = col("!!!! PURCHASE INITIATED !!!!", "green") if m.purchasing == u and m.URL[u][
                                'status'] else instock
                            exc = col(m.URL[u]['exc'], "red")
                            if "purchased" in m.URL[u] and m.URL[u]['prod'] == "test":
                                exc = col("Test passed.", "blue")
                            output_lines[i] = "{}\t|\t\t{}\t\t|\t\t{}\t\t|\t{}\t|{}|{}".format(
                                m.domain,
                                col(m.URL[u]['prod'], "bold"),
                                col(m.URL[u]['price'], "cyan" if m.price_check(u) else "yellow"),
                                instock,
                                col(m.URL[u]['info'], "yellow" if "purchased" not in m.URL[u] else "blue"),
                                exc
                            )
                            i += 1
                        if m.exited:
                            exitc += 1
                            if len(output_lines) > i:
                                output_lines[i] = m.STATUS
                                i += 1
            except KeyboardInterrupt:
                output_lines.append(col("Killing all monitors!", "red"))
                for m in monitors:
                    try:
                        m.kill()
                    except:
                        output_lines.append(m.STATUS)
                        print(os.system(f"taskkill /F /IM Firefox.exe"))
                        exit(0)
                    output_lines.append(m.STATUS)

    def format_url(self, url):
        instock = col("IN STOCK", "green") if url[1]['status'] else col("OUT OF STOCK", "red")
        instock = col("!!!! ATTEMPTING PURCHASE !!!!", "green") if url[1]['purchasing'] and url[1]['status'] else instock
        exc = col(url[1]['exc'], "red")
        if "purchased" in url[1] and url[1]['prod'] == "test":
            exc = col("Test passed.", "blue")
        return "{}\t\t|\t\t{}\t\t|\t{}\t|{}|{}".format(
            url[0].split(".")[1],
            col(url[1]['prod'], "bold"),
            col(url[1]['price'], "cyan" if url[1]['in_budget'] else "yellow"),
            instock,
            col(url[1]['info'], "yellow" if "purchased" not in url[1] else "blue"),
            exc
        )

    def run(self):
        urls = []
        for m in self.monitors:
            urls.extend(list(map(lambda u: (u, m.URL[u]), m.URL)))
        urls = enumerate(urls)
        with output(output_type="dict", interval=50, sort_key=lambda x:"_" in x[0]) as output_lines:
            output_lines['_Monitor'] = f"Domain\t\t\t\t|\t\tProduct\t\t|\t\tPrice|\t\tStatus\t\t|\t\tInfo|Error\t\t|Threads:{threading.activeCount()}"
            while not self.stopped:
                for u in urls:
                    output_lines[str(u[0])]=self.format_url(u[1])
                output_lines['_Status']="OK"

    def kill(self):
        self.stopped=True