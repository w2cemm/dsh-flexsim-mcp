import assert from 'node:assert/strict';
import test from 'node:test';
import path from 'node:path';
import {bridgeConfig, ROOT} from '../dsh/bridge-config.mjs';

test('bundle starts the bundled Python server in UTF-8 with adequate timeout', () => {
  const config = bridgeConfig();
  assert.equal(config.serverName, 'flexsim');
  assert.equal(config.transport, 'stdio');
  assert.deepEqual(config.args, ['-X', 'utf8', path.join(ROOT, 'scripts/launch.py')]);
  assert.ok(config.toolCallTimeoutMs >= 900000);
  assert.equal(config.env.PYTHONIOENCODING, 'utf-8');
});

test('explicit interpreter and shared companion paths survive the bridge', () => {
  const config = bridgeConfig({python: 'custom-python', companionDir: './existing-companion',
    runtimeDir: './shared-runtime', workspaceDir: './中文 工作区'});
  assert.equal(config.command, 'custom-python');
  assert.equal(config.env.FLEXSIM_COMPANION_DIR, path.resolve('./existing-companion'));
  assert.equal(config.env.FLEXSIM_MCP_RUNTIME_DIR, path.resolve('./shared-runtime'));
  assert.equal(config.env.FLEXSIM_WORKSPACE_DIR, path.resolve('./中文 工作区'));
  assert.equal(config.cwd, config.env.FLEXSIM_WORKSPACE_DIR);
});
