"""Loopback-only API port selection checks using synthetic sockets."""

import importlib.util
import socket
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "choose_api_port.py"
SPEC = importlib.util.spec_from_file_location("choose_api_port", SCRIPT_PATH)
PORT_SELECTOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PORT_SELECTOR)


class DevApiPortTests(unittest.TestCase):
    def _held_loopback_port(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        return listener, listener.getsockname()[1]

    def test_skips_a_port_held_by_another_local_service(self):
        occupied, occupied_port = self._held_loopback_port()
        free_probe, next_port = self._held_loopback_port()
        free_probe.close()
        try:
            selected = PORT_SELECTOR.choose_api_port([occupied_port, next_port])
            self.assertEqual(selected, next_port)
            # Selection only probes: the pre-existing listener remains intact.
            self.assertTrue(PORT_SELECTOR.is_loopback_port_available(next_port))
            occupied.getsockname()
        finally:
            occupied.close()

    def test_fails_cleanly_when_no_candidate_port_is_available(self):
        listener, port = self._held_loopback_port()
        try:
            with self.assertRaises(RuntimeError):
                PORT_SELECTOR.choose_api_port([port])
        finally:
            listener.close()

    def test_selected_port_is_not_left_bound(self):
        probe, port = self._held_loopback_port()
        probe.close()

        selected = PORT_SELECTOR.choose_api_port([port])
        self.assertEqual(selected, port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", selected))


if __name__ == "__main__":
    unittest.main()
