"""Install the local DSH bundle and migrate only its FlexSim profile row."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def profile_patch(text: str, config: dict) -> str:
    """Preserve unrelated rows; replace the previous one-row FlexSim block."""
    text = text.replace('\r\n', '\n')
    override = '- id: flexsim-mcp-bridge\n  config:\n'
    override += ''.join('    ' + key + ': ' + json.dumps(value, ensure_ascii=False) + '\n'
                        for key, value in config.items())
    matches = list(re.finditer(r'(?m)^- insert:\n    - id: flexsim-mcp-bridge\n(?:(?:[ \t]+[^\n]*|)\n?)*', text))
    if not matches:
        matches = list(re.finditer(r'(?m)^- id: flexsim-mcp-bridge\n(?:(?:[ \t]+[^\n]*|)\n?)*', text))
    if text.count('id: flexsim-mcp-bridge') != len(matches) or len(matches) > 1:
        raise ValueError('Ambiguous FlexSim rows; inspect the profile patch before changing it')
    if matches:
        match = matches[0]
        if re.search(r'(?m)^    - id:', match.group()[len('- insert:\n    - id: flexsim-mcp-bridge\n'):]):
            raise ValueError('FlexSim shares an insert block with other plugins; migrate it manually')
        return text[:match.start()] + override + text[match.end():]
    return text.rstrip() + '\n\n' + override


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='desktop')
    parser.add_argument('--dsh', default='dsh', help='DSH CLI entry or executable path')
    parser.add_argument('--node', help='Node executable when --dsh points to a JavaScript entry')
    parser.add_argument('--companion', type=Path, default=ROOT / 'companion')
    parser.add_argument('--workspace', type=Path, default=ROOT)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.profile):
        parser.error('Invalid profile name')
    dsh = shutil.which(args.dsh)
    if not dsh and Path(args.dsh).is_file():
        dsh = str(Path(args.dsh).resolve())
    if not dsh:
        parser.error('DSH CLI not found; supply --dsh')
    command = [dsh]
    if Path(dsh).suffix in {'.js', '.mjs', '.cjs'}:
        node = shutil.which(args.node or 'node')
        if not node:
            parser.error('Node not found; supply --node')
        command = [node, dsh]
    companion = args.companion.resolve()
    if not (companion / 'worker.ps1').is_file():
        parser.error('The selected companion does not contain worker.ps1')
    dsh_home = Path(os.environ.get('DSH_HOME', str(Path.home() / '.dsh')))
    profile = dsh_home / 'profiles' / args.profile
    patch_path = profile / 'cordis.patch.yml'
    original = patch_path.read_text(encoding='utf-8-sig') if patch_path.exists() else ''
    config = {'python': sys.executable, 'companionDir': str(companion),
              'runtimeDir': str(companion.parent / 'flexsim-mcp/runtime'),
              'workspaceDir': str(args.workspace.resolve()), 'toolCallTimeoutMs': 900000}
    updated = profile_patch(original, config)
    install_command = command + ['plugin', '--profile', args.profile, 'add', str(ROOT)]
    print(json.dumps({'command': install_command, 'patch': str(patch_path), 'config': config}, ensure_ascii=True, indent=2))
    if args.dry_run:
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = ROOT / '.local' / 'backups' / stamp
    backup.mkdir(parents=True, exist_ok=True)
    for name in ('cordis.patch.yml', 'package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml'):
        source = profile / name
        if source.exists():
            shutil.copy2(source, backup / name)
    print(run(install_command))
    # The CLI owns package/lock/bundle registration; this migrates only the old
    # manual FlexSim insert to an override of the single bundle-owned row.
    current = patch_path.read_text(encoding='utf-8-sig') if patch_path.exists() else ''
    if current != original:
        raise RuntimeError('Profile patch changed during installation; backup saved, migration stopped')
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_patch = patch_path.with_name(patch_path.name + '.' + stamp + '.tmp')
    temporary_patch.write_text(updated, encoding='utf-8', newline='\n')
    os.replace(temporary_patch, patch_path)
    package = json.loads((profile / 'package.json').read_text(encoding='utf-8-sig'))
    bundles = package.get('dsh', {}).get('profile', {}).get('bundles', [])
    if bundles.count('dsh-flexsim-mcp') != 1 or updated.count('id: flexsim-mcp-bridge') != 1:
        raise RuntimeError('DSH bundle/row registration is missing or duplicated')
    try:
        dump = run(command + ['--profile', args.profile, '--dump-config'])
        if 'dsh-flexsim-mcp' not in dump:
            raise RuntimeError('DSH did not compose the new bundle')
        composition = 'verified_by_dump_config'
    except RuntimeError as exc:
        if 'managed exclusively by the Electron application' not in str(exc):
            raise
        dump = 'Desktop profile is managed by Electron; CLI dump-config is unavailable. Restart Desktop to activate.\n'
        composition = 'desktop_managed_registration_verified_restart_required'
    receipt = {'version': '1.2.0', 'installed_at_utc': datetime.now(timezone.utc).isoformat(),
               'repository': 'https://github.com/w2cemm/dsh-flexsim-mcp', 'source': str(ROOT),
               'profile': str(profile), 'config': config, 'backup': str(backup), 'composition': composition,
               'sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ['package.json', 'cordis.patch.yml', 'dsh/index.mjs', 'dsh/bridge-config.mjs', 'scripts/launch.py', 'flexsim-mcp/server.py']}}
    local = ROOT / '.local'
    (local / 'installation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    (local / 'composed-config.txt').write_text(dump, encoding='utf-8')
    print('DSH registration verified; restart DSH to load the new process. Receipt: ' + str(local / 'installation.json'))


if __name__ == '__main__':
    main()
