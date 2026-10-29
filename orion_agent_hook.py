"""Optional local agent activity hook; never executes commands from a payload.

Enable in the small bot: Mərkəz → Canlı işlər → Agent izləməsini aç.
Example: python orion_agent_hook.py --agent Codex --session project1 --state working --label "Faylları oxuyur"
Invoke again with --state completed/error/waiting from your agent's own hook.
"""
import argparse
import json
import sys
import urllib.request
from urllib.parse import urlsplit
import config


def main():
    parser = argparse.ArgumentParser(description='ORION kiçik botuna yerli agentin iş vəziyyətini göndər.')
    parser.add_argument('--agent', required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--state', choices=('working', 'waiting', 'completed', 'error'), required=True)
    parser.add_argument('--label', required=True)
    options = vars(parser.parse_args())
    config.load_env()
    try:
        connection = json.loads((config.data_directory() / 'companion-hook.json').read_text())
        url = urlsplit(connection['url'])
        if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.path != '/api/companion/agent-event':
            raise ValueError('Yerli bağlantı düzgün deyil.')
        request = urllib.request.Request(connection['url'], json.dumps(options).encode(),
                                        {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + connection['token']})
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 200:
                raise ValueError('Agent hadisəsi qəbul edilmədi.')
        print('ORION vəziyyəti qəbul etdi.')
        return 0
    except (OSError, ValueError, KeyError):
        print('ORION işləməlidir və Mərkəz → Canlı işlər bölməsində agent izləməsi açıq olmalıdır.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
