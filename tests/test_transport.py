import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('server_under_test', ROOT / 'flexsim-mcp/server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
installer_spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install_dsh.py')
installer = importlib.util.module_from_spec(installer_spec)
installer_spec.loader.exec_module(installer)


class TransportTests(unittest.TestCase):
    def test_parse_error_replies_then_next_request_still_works(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, FLEXSIM_MCP_SETTINGS=str(Path(temp) / 'absent.json'),
                       FLEXSIM_MCP_RUNTIME_DIR=temp, FLEXSIM_MCP_LOG=str(Path(temp) / 'server.log'))
            data = b'{"secret_script":"must not be logged"\n' + b'\xff\n' + b'[]\n'
            data += json.dumps({'jsonrpc': '2.0', 'id': 4, 'method': 'ping'}).encode() + b'\n'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/launch.py')], input=data,
                                    capture_output=True, env=env, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r['error']['code'] for r in replies[:3]], [-32700, -32700, -32600])
            self.assertEqual(replies[3]['id'], 4)
            self.assertNotIn('must not be logged', (Path(temp) / 'server.log').read_text(encoding='utf-8'))

    def test_bad_arguments_fail_without_desktop_action(self):
        with patch.object(server, 'COMP') as companion:
            for params in ({'name': []}, {'name': 'flexsim_run_script', 'arguments': 'source'}, []):
                response = server.handle({'id': 1, 'method': 'tools/call', 'params': params})
                self.assertEqual(response['error']['code'], -32602)
            companion.call.assert_not_called()

    def test_notification_cannot_execute_a_tool(self):
        with patch.object(server, 'COMP') as companion:
            self.assertIsNone(server.handle({'method': 'tools/call', 'params': {'name': 'flexsim_close'}}))
            companion.call.assert_not_called()

    def test_invalid_unicode_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'invalid Unicode'):
            server.load_script({'text': 'print("\udcb7");'})

    def test_relative_script_uses_configured_workspace_not_client_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / '中文.fs'
            source.write_text('int value = 1;', encoding='utf-8-sig')
            with patch.dict(os.environ, {'FLEXSIM_WORKSPACE_DIR': temp}):
                self.assertEqual(server.load_script({'path': source.name}), 'int value = 1;')

    def test_long_unicode_frame_keeps_tool_error_and_following_ping(self):
        text = '// 中文' + 'x' * 200000
        request = {'id': 2, 'method': 'tools/call', 'params': {'name': 'flexsim_run_script', 'arguments': {'text': text}}}
        with patch.object(server, 'run_script_text', return_value={'verified': True}) as run:
            response = server.dispatch_line(json.dumps(request, ensure_ascii=False).encode())
            self.assertFalse(response['result']['isError'])
            self.assertEqual(run.call_args.args[0], text)
        self.assertEqual(server.dispatch_line(b'{"id":3,"method":"ping"}')['id'], 3)


class InstallerTests(unittest.TestCase):
    def test_migration_preserves_other_rows_and_is_idempotent(self):
        old = '- id: before\n  config:\n    value: true\n- insert:\n    - id: flexsim-mcp-bridge\n      name: old-bridge\n      config:\n        command: old-python\n- id: after\n  config:\n    value: true\n'
        config = {'python': 'C:/Python/python.exe', 'workspaceDir': 'C:/中文 工作区'}
        result = installer.profile_patch(old, config)
        self.assertIn('- id: before\n  config:\n    value: true\n', result)
        self.assertIn('- id: after\n  config:\n    value: true\n', result)
        self.assertEqual(result.count('id: flexsim-mcp-bridge'), 1)
        self.assertEqual(result, installer.profile_patch(result, config))

    def test_shared_or_duplicate_insert_is_not_overwritten(self):
        for text in ('- insert:\n    - id: flexsim-mcp-bridge\n      name: old\n    - id: another-plugin\n      name: keep\n',
                     '- id: flexsim-mcp-bridge\n- id: flexsim-mcp-bridge\n'):
            with self.assertRaises(ValueError):
                installer.profile_patch(text, {'python': 'python'})


if __name__ == '__main__':
    unittest.main()
