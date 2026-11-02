import z from '@deepseek-ai/schemastery';
import {bridgeConfig} from './bridge-config.mjs';

export const name = 'dsh-flexsim-mcp';
export const inject = ['tools'];
export const Config = z.object({
  python: z.string().default('python').description('Python executable; use an absolute path when the Desktop PATH is stale'),
  companionDir: z.string().description('Existing companion directory'),
  runtimeDir: z.string().description('Shared execution receipts and desktop lock directory'),
  workspaceDir: z.string().description('Base directory for relative script paths'),
  flexsimExe: z.string().description('FlexSim executable; must also be allowed by companion'),
  toolCallTimeoutMs: z.number().min(900000).default(900000),
  failOnStartupError: z.boolean().default(false)
});

export async function apply(ctx, config) {
  const bridge = await import('@deepseek-ai/dsh-mcp-client');
  const connection = ctx.plugin(bridge, bridgeConfig(config));
  await connection;
}
