"""Bounded daemon workers. Full application exit never waits on a remote API."""
import concurrent.futures
import queue
import threading


class Executor:
    def __init__(self, workers=2):
        self.queue = queue.Queue(maxsize=16)
        self.closed = False
        for index in range(workers):
            threading.Thread(target=self.run, daemon=True, name=f"orion-worker-{index}").start()

    def submit(self, fn, *args):
        if self.closed:
            raise RuntimeError("ORION bağlanır.")
        future = concurrent.futures.Future()
        try:
            self.queue.put_nowait((future, fn, args))
        except queue.Full:
            raise ValueError("Tapşırıq növbəsi doludur.") from None
        return future

    def run(self):
        while True:
            item = self.queue.get()
            if item is None:
                return
            future, fn, args = item
            if future.set_running_or_notify_cancel():
                try:
                    future.set_result(fn(*args))
                except BaseException as error:
                    future.set_exception(error)

    def shutdown(self, **_):
        if self.closed:
            return
        self.closed = True
        while True:
            try:
                item = self.queue.get_nowait()
                if item:
                    item[0].cancel()
            except queue.Empty:
                break
        self.queue.put_nowait(None)
        self.queue.put_nowait(None)
