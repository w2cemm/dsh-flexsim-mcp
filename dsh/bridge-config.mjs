import path from 'node:path';
import {fileURLToPath} from 'node:url';

export const ROOT = fileURLToPath(new URL('../', import.meta.url));

export function bridgeConfig(config = {}) {
  const env = {PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8'};
  const variables = {companionDir: 'FLEXSIM_COMPANION_DIR', runtimeDir: 'FLEXSIM_MCP_RUNTIME_DIR',
    workspaceDir: 'FLEXSIM_WORKSPACE_DIR', flexsimExe: 'FLEXSIM_EXE'};
  for (const [key, variable] of Object.entries(variables)) {
    if (config[key]) env[variable] = path.resolve(config[key]);
  }
  return {serverName: 'flexsim', transport: 'stdio', command: config.python || 'python',
    args: ['-X', 'utf8', path.join(ROOT, 'scripts', 'launch.py')],
    cwd: config.workspaceDir ? path.resolve(config.workspaceDir) : ROOT,
    env, toolCallTimeoutMs: config.toolCallTimeoutMs ?? 900000,
    failOnStartupError: config.failOnStartupError ?? false,
    reconnect: {enabled: true, initialDelayMs: 1000, maxDelayMs: 30000, maxAttempts: 5}};
}
