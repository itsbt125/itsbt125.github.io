from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote
from urllib.request import urlopen
import json

LOKI = "http://localhost:3100"
PROMETHEUS = "http://localhost:9090/api/v1/query"
PORT = 9091

def query(q):
    with urlopen(f"{PROMETHEUS}?query={quote(q)}") as r:
        return float(json.loads(r.read())["data"]["result"][0]["value"][1])

def get_visitors():
    q = quote('{job="nginx"} | pattern `<remote_addr> - - [<_>] "<_>" <_> <_> "<_>" "<_>"` | remote_addr!="::1"')
    with urlopen(f"{LOKI}/loki/api/v1/query_range?query={q}&start={int(__import__('time').time()) - 86400}&end={int(__import__('time').time())}&limit=5000") as r:
        streams = json.loads(r.read())["data"]["result"]
    ips = set()
    for stream in streams:
        for entry in stream["values"]:
            line = entry[1]
            ip = line.split(" ")[0]
            if ip and ip != "::1":
                ips.add(ip)
    return len(ips)

def get_stats():
    return {
        "info": "hi there, this is an endpoint for my server that returns stats from my locally hosted grafana dasboard w/ loki and prometheus!",
        "mem_used": round(query("(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024 / 1024"), 2),
        "cpu": round(query('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'), 1),
        "uptime": int(query("time() - node_boot_time_seconds")),
        "unique_visitors_by_ip": get_visitors()
    }

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/stats":
            self.send_response(404)
            self.end_headers()
            return

        try:
            data = json.dumps(get_stats()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, *args):
        pass

HTTPServer(("", PORT), Handler).serve_forever()
