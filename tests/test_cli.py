"""Exercise the installed console entry point, not parser internals."""

from pathlib import Path
import subprocess
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

from auralytica import main


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        executable = Path(sys.executable).parent / "auralytica"
        return subprocess.run(
            [str(executable), *args], capture_output=True, text=True, timeout=10
        )

    def test_help_explains_the_application(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: auralytica", result.stdout)
        self.assertIn("Takeout", result.stdout)

    def test_no_arguments_shows_help(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: auralytica", result.stdout)

    def test_unknown_command_fails_instead_of_reporting_success(self):
        result = self.run_cli("not-a-command")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not-a-command", result.stderr)

    def test_import_folder_returns_counts_and_reuses_same_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'watch-history.json').write_text(json.dumps([
                {'titleUrl':'https://youtu.be/abcdefghijk', 'title':'Watched Song'}
            ]))
            args = ('import', folder, '--database', str(root/'state.sqlite3'))
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['statistics']['unique_videos'],1)
            self.assertTrue(json.loads(self.run_cli(*args).stdout)['reused'])

    def test_import_missing_folder_reports_actionable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.run_cli('import', str(Path(folder)/'missing'), '--database', str(Path(folder)/'state.sqlite3'))
            self.assertEqual(result.returncode,2)
            self.assertIn('Folder Takeout', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_classify_requires_import_and_can_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            args=('classify','--database',str(root/'state.sqlite3'))
            result=self.run_cli(*args)
            self.assertEqual(result.returncode,2)
            self.assertIn('import Takeout',result.stderr)
            (root/'watch-history.json').write_text('[]')
            self.assertEqual(self.run_cli('import',folder,'--database',str(root/'state.sqlite3')).returncode,0)
            result=self.run_cli(*args)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['counts'],{'music':0,'rest':0})

    def test_list_and_move_share_persisted_membership(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            database=str(root/'state.sqlite3')
            (root/'watch-history.json').write_text(json.dumps([{'titleUrl':'https://youtu.be/abcdefghijk','title':'Song'}]))
            self.assertEqual(self.run_cli('import',folder,'--database',database).returncode,0)
            result=self.run_cli('list','--group','rest','--database',database)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['filtered_count'],1)
            result=self.run_cli('move','abcdefghijk','--to','music','--database',database)
            self.assertEqual(result.returncode,0,result.stderr)
            result=self.run_cli('list','--group','music','--search','song','--page-size','1','--database',database)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['items'][0]['decision_source'],'user')
            result=self.run_cli('move','missing0000','--to','rest','--database',database)
            self.assertEqual(result.returncode,2)
            self.assertNotIn('Traceback',result.stderr)

    def test_serve_uses_loopback_and_requested_port(self):
        with tempfile.TemporaryDirectory() as folder:
            database=str(Path(folder)/'state.sqlite3')
            with patch.object(sys,'argv',['auralytica','serve','--database',database,'--port','8766']), patch('uvicorn.run') as run:
                main()
            self.assertEqual(run.call_args.kwargs['host'],'127.0.0.1')
            self.assertEqual(run.call_args.kwargs['port'],8766)
            self.assertFalse(run.call_args.kwargs['proxy_headers'])

    def test_serve_rejects_invalid_port_and_network_host(self):
        for args in (('serve','--port','0'),('serve','--host','0.0.0.0')):
            result=self.run_cli(*args)
            self.assertEqual(result.returncode,2,result.stderr)


if __name__ == "__main__":
    unittest.main()
