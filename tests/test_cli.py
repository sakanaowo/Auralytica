"""Exercise the installed web-only launcher and its port ownership rules."""

from pathlib import Path
import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen
from unittest.mock import Mock, patch

import auralytica


class LauncherTests(unittest.TestCase):
    def run_cli(self, *args):
        executable = Path(sys.executable).parent / 'auralytica'
        return subprocess.run([str(executable), *args], capture_output=True, text=True, timeout=10)

    def test_help_describes_web_launcher_without_business_commands(self):
        result = self.run_cli('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('giao diện web local', result.stdout)
        for command in ('import', 'classify', 'list', 'move', 'metadata', 'audit',
                        'download', 'status', 'stop', 'resume', 'classification-preview'):
            self.assertNotIn(f'  {command}', result.stdout)

    def test_no_arguments_launches_default_database_port_and_browser(self):
        with patch.object(sys, 'argv', ['auralytica']), patch('auralytica.launch') as launch:
            auralytica.main()
        launch.assert_called_once_with(
            Path.home()/'.local/share/auralytica/library.sqlite3',
            port=8765,
            open_browser=True,
        )

    def test_options_launch_loopback_and_can_disable_browser(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder)/'state.sqlite3'
            run_server = Mock()
            result = auralytica.launch(database, port=8766, open_browser=False,
                                        run_server=run_server)
        self.assertEqual(result, 'started')
        kwargs = run_server.call_args.kwargs
        self.assertEqual((kwargs['host'], kwargs['port']), ('127.0.0.1', 8766))
        self.assertFalse(kwargs['proxy_headers'])

    def test_existing_verified_instance_is_reused_only_for_same_database(self):
        database = Path('/tmp/auralytica-launcher.sqlite3')
        opened, run_server = Mock(), Mock()
        expected = auralytica.database_identity(database)
        with patch('auralytica._port_in_use', return_value=True), \
             patch('auralytica._probe_instance', return_value={'app': 'auralytica', 'api': 1,
                                                               'database_id': expected}):
            result = auralytica.launch(database, browser_open=opened, run_server=run_server)
        self.assertEqual(result, 'reused')
        opened.assert_called_once_with('http://127.0.0.1:8765')
        run_server.assert_not_called()

    def test_new_instance_opens_browser_only_after_health_matches(self):
        database = Path('/tmp/auralytica-launcher.sqlite3')
        expected = {'app': 'auralytica', 'api': 1,
                    'database_id': auralytica.database_identity(database)}
        opened = Mock()
        with patch('auralytica._probe_instance', side_effect=[None, expected]), \
             patch('auralytica.time.sleep'):
            auralytica._open_when_ready('http://127.0.0.1:8765', database, opened)
        opened.assert_called_once_with('http://127.0.0.1:8765')

    def test_foreign_or_other_database_port_is_not_killed_or_reused(self):
        database = Path('/tmp/auralytica-launcher.sqlite3')
        for identity in (None, {'app': 'other'},
                         {'app': 'auralytica', 'api': 1, 'database_id': 'different'}):
            with self.subTest(identity=identity), patch('auralytica._port_in_use', return_value=True), \
                 patch('auralytica._probe_instance', return_value=identity):
                with self.assertRaisesRegex(auralytica.LauncherError, '8765'):
                    auralytica.launch(database, run_server=Mock(), browser_open=Mock())

    def test_old_business_command_is_rejected(self):
        result = self.run_cli('import', '/tmp/Takeout')
        self.assertEqual(result.returncode, 2)
        self.assertIn('unrecognized arguments', result.stderr)

    def test_invalid_port_and_network_host_are_rejected(self):
        for args in (('--port', '0'), ('--host', '0.0.0.0')):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)

    def test_desktop_entry_starts_launcher_without_terminal(self):
        entry = Path('packaging/auralytica.desktop').read_text()
        self.assertIn('Exec=auralytica', entry)
        self.assertIn('Terminal=false', entry)
        self.assertIn('Type=Application', entry)

    def test_real_launcher_reuses_matching_instance_and_rejects_other_database(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = temp.name
        with socket.socket() as available:
            available.bind(('127.0.0.1', 0))
            port = available.getsockname()[1]
            database = Path(folder)/'state.sqlite3'
        executable = Path(sys.executable).parent/'auralytica'
        process = subprocess.Popen(
            [str(executable), '--no-browser', '--port', str(port), '--database', str(database)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(80):
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/health', timeout=.5) as response:
                        identity = json.load(response)
                    break
                except OSError:
                    time.sleep(.05)
            else:
                self.fail('Launcher did not start its loopback server.')
            self.assertEqual(identity['database_id'], auralytica.database_identity(database))
            reused = subprocess.run(
                [str(executable), '--no-browser', '--port', str(port), '--database', str(database)],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(reused.returncode, 0, reused.stderr)
            rejected = subprocess.run(
                [str(executable), '--no-browser', '--port', str(port), '--database', str(Path(folder)/'other.sqlite3')],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn(f'Cổng {port}', rejected.stderr)
            self.assertIsNone(process.poll())
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    unittest.main()
