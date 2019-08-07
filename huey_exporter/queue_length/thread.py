import time
from threading import Thread
from prometheus_client import Gauge

from huey_exporter.queue_length.explorer import HueyExplorer, HueyQueue
from ..exporter_logging import logger

TASK_COUNT_GAUGE = Gauge('hueyx_queue_task_count', 'Huey queue length', ['queue_name', 'task_name'])


class QueueLengthThread(Thread):
    def __init__(self, connection_pool, pull_time_in_seconds=10):
        super(QueueLengthThread, self).__init__()
        self.stop = False
        self.explorer = HueyExplorer(connection_pool)
        self.pull_time_in_seconds = pull_time_in_seconds

    def run(self):
        try:
            logger.info('Started queue length thread')
            while not self.stop:

                for queue in self.explorer.cached_queues:
                    self._report_queue(queue)

                for i in range(0, self.pull_time_in_seconds):
                    if self.stop:
                        break
                    time.sleep(1)
        except Exception as e:
            logger.error(f'Error in QueueLengthThread. {e}')
        logger.info('Exit run method of thread')


    def _report_queue(self, queue: HueyQueue):
        logger.info(f'Queue {queue.name} length {len(queue)}')
        logger.info(f'Tasks: {queue.tasks}')
        for task, count in queue.tasks.items():
            TASK_COUNT_GAUGE.labels(queue_name=queue.name, task_name=task).set(count)

    def exit_gracefully(self):
        self.stop = True
