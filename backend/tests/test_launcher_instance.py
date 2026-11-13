"""Başlatıcı yalnızca arayüzü sunan gerçek masaüstü örneğine yönlenmeli."""

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from kelebek import launcher


def _serve(health: dict, root_status: int, root_body: bytes) -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/health":
                status, body = 200, json.dumps(health).encode()
            else:
                status, body = root_status, root_body
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class RunningInstanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.instance = Path(self.tmp.name) / "instance.json"
        patcher = mock.patch.object(launcher, "_instance_file", return_value=self.instance)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _record(self, health, root_status=200, root_body=b'<div id="root"></div>'):
        server = _serve(health, root_status, root_body)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_address[1]
        self.instance.write_text(json.dumps({"port": port, "pid": 1}), encoding="utf-8")
        return f"http://127.0.0.1:{port}"

    def test_real_desktop_instance_is_reused(self):
        url = self._record({"status": "ok", "service": "kelebek-sinav-sistemi", "desktop": True})
        self.assertEqual(launcher._running_instance_url(), url)

    def test_api_only_dev_server_is_ignored(self):
        self._record({"status": "ok", "service": "kelebek-sinav-sistemi", "desktop": False}, 404, b"Not Found")
        self.assertIsNone(launcher._running_instance_url())

    def test_instance_without_frontend_is_ignored(self):
        self._record({"status": "ok", "service": "kelebek-sinav-sistemi", "desktop": True}, 404, b"Not Found")
        self.assertIsNone(launcher._running_instance_url())

    def test_foreign_service_is_ignored(self):
        self._record({"status": "ok"})
        self.assertIsNone(launcher._running_instance_url())

    def test_missing_or_broken_record_is_ignored(self):
        self.assertIsNone(launcher._running_instance_url())
        self.instance.write_text("{bozuk", encoding="utf-8")
        self.assertIsNone(launcher._running_instance_url())


class StopServerTests(unittest.TestCase):
    def test_stop_ends_the_server_even_while_a_browser_keeps_its_connection_open(self):
        # Gerileme: pencere ya da sekme bağlantısını açık tuttuğu sürece servis döngüsü bitmiyor,
        # "Uygulamayı kapat" düğmesinden sonra uygulama arka planda çalışmaya devam ediyordu.
        import socket

        from waitress.server import create_server

        def wsgi(environ, start_response):
            start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", "2")])
            return [b"ok"]

        server = create_server(wsgi, host="127.0.0.1", port=0, threads=2)
        port = server.effective_port
        worker = threading.Thread(target=server.run, daemon=True)
        worker.start()
        client = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.addCleanup(client.close)
        client.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n")
        self.assertIn(b"200 OK", client.recv(4096))

        launcher.stop_server(server)
        worker.join(timeout=5)
        self.assertFalse(worker.is_alive(), "Servis, açık bağlantı yüzünden durmadı.")


class WindowedModeTests(unittest.TestCase):
    """Komut penceresi olmadan (pencereli kip) açılış."""

    def test_missing_streams_are_replaced_so_writes_do_not_crash(self):
        with mock.patch.object(launcher.sys, "stdout", None), mock.patch.object(launcher.sys, "stderr", None):
            launcher._ensure_standard_streams()
            print("çıktı", file=launcher.sys.stdout, flush=True)
            print("hata", file=launcher.sys.stderr, flush=True)
            launcher.sys.stdout.close()
            launcher.sys.stderr.close()

    def test_startup_failure_is_logged_and_exits_with_an_error_code(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(launcher, "get_data_dir", return_value=Path(folder)), \
                mock.patch.object(launcher, "_run", side_effect=RuntimeError("port alınamadı")), \
                mock.patch.object(launcher.sys, "platform", "linux"):  # Windows'ta ileti kutusu testi bekletmesin
            with self.assertRaises(SystemExit) as stopped:
                launcher.main()
            self.assertEqual(stopped.exception.code, 1)
            log = (Path(folder) / "logs" / "launcher-error.log").read_text(encoding="utf-8")
        self.assertIn("port alınamadı", log)


if __name__ == "__main__":
    unittest.main()
