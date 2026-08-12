import http.server
import threading
import webbrowser
import time
import dashboard

PORT = 18270
server = http.server.HTTPServer(("127.0.0.1", PORT), dashboard._DashboardHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
webbrowser.open(f"http://localhost:{PORT}/config")
while True:
    time.sleep(60)