import time

class Daemon(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._daemon = True

    def _run(self):
        while True:
            self._run_once()
            time.sleep(self._interval)

    def _run_once(self):
        raise NotImplementedError

    def run(self):
        self._run_once()
        self._run()