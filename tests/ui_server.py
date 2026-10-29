"""Disposable local runtime for browser regression tests; no .env or services."""
import signal
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard_bridge import start
from engine import Engine


def run():
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    with tempfile.TemporaryDirectory(prefix='orion-ui-test-') as directory:
        engine = Engine(directory)
        server = start(0, engine)
        print(f'http://127.0.0.1:{server.server_address[1]}', flush=True)
        try:
            stopped.wait()
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
            engine.close()


if __name__ == '__main__':
    run()
