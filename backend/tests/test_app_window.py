"""Uygulama penceresi: tarayıcı sekmesi yerine adres çubuksuz, bağımsız pencere."""

import tempfile
import unittest
from pathlib import Path

from kelebek import app_window


class FindBrowserTests(unittest.TestCase):
    def test_windows_prefers_edge_which_ships_with_the_system(self):
        edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        env = {"ProgramFiles(x86)": r"C:\Program Files (x86)", "ProgramFiles": r"C:\Program Files",
               "LOCALAPPDATA": r"C:\Users\x\AppData\Local"}
        found = app_window.find_app_browser("win32", env, which=lambda name: None,
                                            exists=lambda path: path in {edge, chrome})
        self.assertEqual(found, edge)

    def test_windows_falls_back_to_chrome(self):
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        env = {"ProgramFiles(x86)": r"C:\Program Files (x86)", "ProgramFiles": r"C:\Program Files"}
        found = app_window.find_app_browser("win32", env, which=lambda name: None,
                                            exists=lambda path: path == chrome)
        self.assertEqual(found, chrome)

    def test_macos_uses_an_installed_chromium_family_browser(self):
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        found = app_window.find_app_browser("darwin", {"HOME": "/Users/x"}, which=lambda name: None,
                                            exists=lambda path: path == chrome)
        self.assertEqual(found, chrome)

    def test_linux_looks_the_browser_up_on_the_path(self):
        found = app_window.find_app_browser(
            "linux", {}, which=lambda name: "/usr/bin/chromium" if name == "chromium" else None,
            exists=lambda path: False)
        self.assertEqual(found, "/usr/bin/chromium")

    def test_nothing_suitable_means_no_window(self):
        for platform in ("win32", "darwin", "linux"):
            self.assertIsNone(app_window.find_app_browser(platform, {}, which=lambda name: None,
                                                          exists=lambda path: False))


class CommandTests(unittest.TestCase):
    def test_command_opens_the_address_as_an_app_with_its_own_profile(self):
        command = app_window.build_command("/usr/bin/chromium", "http://127.0.0.1:5123", Path("/veri/pencere"),
                                           platform="linux")
        self.assertEqual(command[0], "/usr/bin/chromium")
        self.assertIn("--app=http://127.0.0.1:5123", command)
        self.assertIn(f"--user-data-dir={Path('/veri/pencere')}", command)
        self.assertIn("--no-first-run", command)
        # Pencere kapanınca tarayıcı arka planda açık kalmamalı; uygulama kapanışı buna bağlı.
        self.assertIn("--disable-background-mode", command)
        self.assertIn("--class=kelebek-sinav-sistemi", command)
        self.assertIn("--disable-features=Translate", command)

    def test_window_class_is_only_set_on_linux(self):
        command = app_window.build_command("msedge.exe", "http://127.0.0.1:1", Path("p"), platform="win32")
        self.assertFalse(any(part.startswith("--class=") for part in command))


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)

    def test_window_mode_is_on_by_default(self):
        self.assertTrue(app_window.window_mode_enabled(self.data_dir, {}))

    def test_setting_and_environment_switch_it_off(self):
        app_window.set_window_mode(self.data_dir, False)
        self.assertFalse(app_window.window_mode_enabled(self.data_dir, {}))
        app_window.set_window_mode(self.data_dir, True)
        self.assertTrue(app_window.window_mode_enabled(self.data_dir, {}))
        self.assertFalse(app_window.window_mode_enabled(self.data_dir, {"KELEBEK_BROWSER_TAB": "1"}))

    def test_setting_keeps_other_stored_preferences(self):
        (self.data_dir / "ui_state.json").write_text('{"last_seen_version": "0.9.3"}', encoding="utf-8")
        app_window.set_window_mode(self.data_dir, False)
        import json
        state = json.loads((self.data_dir / "ui_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state, {"last_seen_version": "0.9.3", "app_window": False})


class OpenWindowTests(unittest.TestCase):
    def test_open_starts_the_browser_and_returns_the_process(self):
        started = {}

        def popen(command, **kwargs):
            started["command"] = command
            return "süreç"

        with tempfile.TemporaryDirectory() as folder:
            process = app_window.open_app_window(
                "http://127.0.0.1:5123", Path(folder), platform="linux", env={},
                which=lambda name: "/usr/bin/chromium" if name == "chromium" else None,
                exists=lambda path: False, popen=popen)
            self.assertEqual(process, "süreç")
            self.assertIn("--app=http://127.0.0.1:5123", started["command"])
            self.assertTrue((Path(folder) / "window-profile").is_dir())

    def test_open_returns_none_without_a_browser_or_when_start_fails(self):
        def failing(command, **kwargs):
            raise OSError("başlatılamadı")

        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(app_window.open_app_window(
                "http://127.0.0.1:1", Path(folder), platform="linux", env={},
                which=lambda name: None, exists=lambda path: False, popen=failing))
            with self.assertLogs("kelebek.app_window", level="WARNING"):
                self.assertIsNone(app_window.open_app_window(
                    "http://127.0.0.1:1", Path(folder), platform="linux", env={},
                    which=lambda name: "/usr/bin/chromium", exists=lambda path: False, popen=failing))


class WindowLifecycleTests(unittest.TestCase):
    class FakeProcess:
        def __init__(self, exits_after):
            self.exits_after = exits_after
            self.terminated = False

        def wait(self, timeout=None):
            import subprocess
            if timeout is not None and timeout < self.exits_after:
                raise subprocess.TimeoutExpired("pencere", timeout)
            return 0

        def poll(self):
            return 0 if self.terminated else None

        def terminate(self):
            self.terminated = True

    def test_closing_the_window_stops_the_application(self):
        stopped = []
        app_window.watch_window(self.FakeProcess(exits_after=30), lambda: stopped.append(True),
                                handoff_seconds=3, background=False)
        self.assertEqual(stopped, [True])

    def test_an_immediate_exit_is_a_handoff_and_does_not_stop_the_application(self):
        # Aynı profilde açık bir pencere varsa tarayıcı adresi ona devredip hemen çıkar.
        stopped = []
        app_window.watch_window(self.FakeProcess(exits_after=0.5), lambda: stopped.append(True),
                                handoff_seconds=3, background=False)
        self.assertEqual(stopped, [])

    def test_close_window_terminates_a_running_process_only(self):
        process = self.FakeProcess(exits_after=30)
        app_window.close_window(process)
        self.assertTrue(process.terminated)
        app_window.close_window(None)  # pencere yoksa sessizce geçer


class OpenInterfaceTests(unittest.TestCase):
    """Başlatıcı: pencere açılabiliyorsa pencere, açılamıyorsa eskisi gibi tarayıcı sekmesi."""

    def setUp(self):
        from unittest import mock

        from kelebek import launcher
        self.launcher, self.mock = launcher, mock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data_dir = Path(self.tmp.name)

    def _open(self, window_process, env=None):
        with self.mock.patch.object(app_window, "open_app_window", return_value=window_process) as opened, \
                self.mock.patch.object(app_window, "watch_window") as watched, \
                self.mock.patch.object(self.launcher.webbrowser, "open") as tab:
            result = self.launcher.open_interface("http://127.0.0.1:5123", self.data_dir, env or {}, lambda: None)
        return result, opened, watched, tab

    def test_window_is_opened_and_watched_instead_of_a_browser_tab(self):
        result, opened, watched, tab = self._open("süreç")
        self.assertEqual(result, "süreç")
        opened.assert_called_once()
        watched.assert_called_once()
        tab.assert_not_called()

    def test_browser_tab_is_the_fallback_when_no_window_can_be_opened(self):
        result, _opened, watched, tab = self._open(None)
        self.assertIsNone(result)
        watched.assert_not_called()
        tab.assert_called_once_with("http://127.0.0.1:5123")

    def test_window_mode_switched_off_goes_straight_to_the_browser_tab(self):
        app_window.set_window_mode(self.data_dir, False)
        result, opened, _watched, tab = self._open("süreç")
        self.assertIsNone(result)
        opened.assert_not_called()
        tab.assert_called_once()


class WindowSettingApiTests(unittest.TestCase):
    def setUp(self):
        import os
        from unittest import mock

        from kelebek import create_app
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"KELEBEK_DATA_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        app = create_app()
        self.addCleanup(lambda: app.extensions["kelebek_engine"].dispose())
        self.client = app.test_client()

    def test_setting_is_reported_and_can_be_changed(self):
        self.assertTrue(self.client.get("/api/app/window-mode").get_json()["enabled"])
        changed = self.client.put("/api/app/window-mode", json={"enabled": False})
        self.assertEqual(changed.status_code, 200, changed.get_json())
        self.assertFalse(self.client.get("/api/app/window-mode").get_json()["enabled"])
        self.assertFalse(app_window.window_mode_enabled(Path(self.tmp.name), {}))

    def test_invalid_value_is_rejected(self):
        self.assertEqual(self.client.put("/api/app/window-mode", json={"enabled": "evet"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
