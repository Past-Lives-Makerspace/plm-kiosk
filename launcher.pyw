"""PLM Kiosk Launcher — fullscreen native window with IPC for remote control."""

import time
import socket
import threading
import urllib.request
import webview

IPC_PORT = 51988  # one above the wallpaper engine

class KioskServer:
    """TCP IPC server for remote control of the kiosk window."""
    def __init__(self, window):
        self.window = window
        self.running = True
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.settimeout(1.0)
        try:
            srv.bind(("0.0.0.0", IPC_PORT))
        except OSError:
            print(f"WARN: Could not bind IPC port {IPC_PORT}", flush=True)
            return
        srv.listen(1)
        while self.running:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            try:
                data = conn.recv(4096).decode().strip()
                resp = self._handle(data)
                conn.sendall(resp.encode())
            except Exception as e:
                try:
                    conn.sendall(f"ERROR: {e}".encode())
                except:
                    pass
            finally:
                conn.close()
        srv.close()

    def _handle(self, cmd):
        action = cmd.lower().split()[0] if cmd else ""

        if action == "reload":
            self.window.evaluate_js("window.location.href='/?r=' + Date.now()")
            return "OK: reloaded"
        elif action == "ping":
            return "pong"
        elif action == "stop":
            self.running = False
            self.window.destroy()
            return "OK: stopping"
        elif action == "url":
            url = self.window.get_current_url() or "unknown"
            return f"OK: {url}"
        else:
            return f"ERROR: unknown command: {action}"

    def stop(self):
        self.running = False


def wait_for_server(url="http://127.0.0.1:5000", timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


if __name__ == "__main__":
    wait_for_server()

    window = webview.create_window(
        "Past Lives Makerspace",
        "http://127.0.0.1:5000",
        fullscreen=True,
        frameless=True,
        easy_drag=False,
        text_select=False,
    )

    server = [None]

    def on_shown():
        server[0] = KioskServer(window)
        print("Kiosk IPC server running on port 51988", flush=True)

    def on_closing():
        if server[0]:
            server[0].stop()
        return True

    window.events.shown += on_shown
    window.events.closing += on_closing

    webview.start()
