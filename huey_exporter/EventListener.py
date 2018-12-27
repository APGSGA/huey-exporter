import re
import time
from datetime import datetime, timedelta
from typing import List, Set

from huey.consumer import EVENT_FINISHED, EVENT_STARTED, EVENT_ERROR_TASK
from prometheus_client import Summary, Counter
from redis.client import PubSub, Redis

from huey_exporter.RedisEnqueuedEventHuey import EVENT_ENQUEUED
from huey_exporter.explorer import CachedRedisExplorer
from huey_exporter.exporter_logging import logger
import json

# Create a metric to track time spent and requests made.
ENQUEUED_COUNTER = Counter('huey_enqueued_tasks', 'Huey Tasks enqueued', ['queue_name', 'task_name'])
STARTED_COUNTER = Counter('huey_started_tasks', 'Huey Tasks started', ['queue_name', 'task_name'])
FINISHED_COUNTER = Counter('huey_finished_tasks', 'Huey Tasks Finished', ['queue_name', 'task_name'])
ERROR_COUNTER = Counter('huey_error_tasks', 'Huey Task Errors', ['queue_name', 'task_name'])
TASK_DURATION_SUMMARY = Summary('huey_task_duration_seconds', 'Time spent processing tasks', ['queue_name', 'task_name'])


class Timer:
    def __init__(self):
        self.start_time: datetime = None
        self.end_time: datetime = None

    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def current_duration(self) -> timedelta:
        return datetime.now() - self.start_time

    def start(self):
        self.start_time = datetime.now()

    def end(self):
        self.end_time = datetime.now()


class QueueSubscription:
    def __init__(self, connection_pool):
        self.redis = Redis(connection_pool=connection_pool)
        self.redis_pubsub: PubSub = self.redis.pubsub()
        self._is_subscribed = False

    def get_message(self, timeout):
        return self.redis_pubsub.get_message(timeout=timeout)

    def subscribe(self, queue_names: List[str]):
        logger.info('subscribe to {}'.format(queue_names))
        if self._is_subscribed:
            self.redis_pubsub.unsubscribe()
            self._is_subscribed = False
        self.redis_pubsub.subscribe(queue_names)
        self._is_subscribed = True


class EventListener:



    def __init__(self, connection_pool, queue_name_expires_in=60*30):
        self.queue_explorer = CachedRedisExplorer(connection_pool, expiring_in=queue_name_expires_in)
        self.subscription: QueueSubscription = QueueSubscription(connection_pool)
        self.event_handlers = {
            EVENT_FINISHED: self.event_finished,
            EVENT_ENQUEUED: self.event_enqueued,
            EVENT_STARTED: self.event_started,
            EVENT_ERROR_TASK: self.event_error,
        }

    def _queue_names(self) -> Set[str]:
        return self.queue_explorer.queue_names

    def pull_cleaned_queue_names(self) -> List[str]:
        return self._clean_queue_names(list(self._queue_names()))

    def wait_on_queue_names(self) -> List[str]:
        """
        Waits until at least one queue name is received.
        :return:
        """
        while True:
            queue_names = self.pull_cleaned_queue_names()
            if len(queue_names) > 0:
                return queue_names
            time.sleep(1)
            logger.warning('No huey queue found. Try again in 1 seconds.')

    def listen(self):
        """
        Listens to the queues and actively explorers queue names.
        :return:
        """

        queue_names = self.wait_on_queue_names()
        self.subscription.subscribe(queue_names)
        while True:
            self.listen_cicle()
            new_queue_names = self.wait_on_queue_names()
            if new_queue_names != queue_names:
                queue_names = new_queue_names
                self.subscription.subscribe(queue_names)

    def listen_cicle(self, timeout=2):
        """
        Listens to the events till the timeout expires.
        :param timeout: in seconds
        :return:
        """
        timer = Timer()
        timer.start()
        while True:
            if timer.current_duration > timedelta(seconds=timeout):
                break
            event = self.subscription.get_message(timeout=0.3)

            if event is None:
                continue
            if event['type'] != 'message':
                continue

            channel = event['channel'].decode('utf-8')
            data = json.loads(event['data'].decode('utf-8'))
            logger.debug('Received event from {}: {}'.format(channel, json.dumps({'data': data})))

            self.handle_event(channel, data)

    def handle_event(self, queue_name: str, event: {}):
        try:
            event_handler = self.event_handlers[event['status']]
            event_handler(queue_name, event)

        except KeyError:
            logger.debug('Ignored event {status}'.format(status=event['status']))

    def event_enqueued(self, queue_name, event):
        ENQUEUED_COUNTER.labels(**self.labels(queue_name, event)).inc()

    def event_started(self, queue_name, event):
        STARTED_COUNTER.labels(**self.labels(queue_name, event)).inc()

    def event_finished(self, queue_name, event):
        FINISHED_COUNTER.labels(**self.labels(queue_name, event)).inc()
        TASK_DURATION_SUMMARY.labels(**self.labels(queue_name, event)).observe(event['duration'])

    def event_error(self, queue_name, event):
        ERROR_COUNTER.labels(**self.labels(queue_name, event)).inc()

    def labels(self, queue_name, event):
        return {
            'queue_name': queue_name,
            'task_name': self.clean_event_name(event['task'])
        }

    def clean_event_name(self, name):
        prefix = 'queue_task_'
        return name[len(prefix):]

    # Copied from https://github.com/coleifer/huey/blob/1.9.1/huey/storage.py#L302
    def _clean_queue_name(self, name):
        return re.sub('[^a-z0-9]', '', name)

    def _clean_queue_names(self, names: List[str]):
        cleaned = []
        for name in names:
            cleaned.append(self._clean_queue_name(name))
        return cleaned
