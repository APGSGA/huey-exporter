import time
from threading import Thread
import signal
from prometheus_client import Gauge

from huey_exporter.queue_length.explorer import HueyExplorer
from ..exporter_logging import logger

GAUGE = Gauge('hueyx_queue_length', 'Huey queue length', ['queue_name'])


class QueueLengthThread(Thread):
    def __init__(self, connection_pool):
        super(QueueLengthThread, self).__init__()
        self.stop = False
        self.explorer = HueyExplorer(connection_pool)

    def run(self):
        logger.info('Started queue length thread')
        while not self.stop:

            for queue in self.explorer.cached_queues:
                length = len(queue)
                logger.info(f'Queue {queue.name} length {length}')
                GAUGE.labels(queue_name=queue.name).set(length)

            for i in range(0, 10):
                if self.stop:
                    break
                time.sleep(i)
        logger.info('Exit run method of thread')

    def exit_gracefully(self):
        self.stop = True
