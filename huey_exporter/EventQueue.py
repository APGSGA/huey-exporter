import re
from typing import List

from huey.consumer import EVENT_FINISHED, EVENT_STARTED, EVENT_ERROR_TASK
from prometheus_client import Summary, Counter
from redis.client import PubSub, Redis

from huey_exporter.RedisEnqueuedEventHuey import EVENT_ENQUEUED
from huey_exporter.exporter_logging import logger
import json

# Create a metric to track time spent and requests made.
ENQUEUED_COUNTER = Counter('huey_enqueued_tasks', 'Huey Tasks enqueued', ['queue_name', 'task_name'])
STARTED_COUNTER = Counter('huey_started_tasks', 'Huey Tasks started', ['queue_name', 'task_name'])
FINISHED_COUNTER = Counter('huey_finished_tasks', 'Huey Tasks Finished', ['queue_name', 'task_name'])
ERROR_COUNTER = Counter('huey_error_tasks', 'Huey Task Errors', ['queue_name', 'task_name'])
TASK_DURATION_SUMMARY = Summary('huey_task_duration_seconds', 'Time spent processing tasks', ['queue_name', 'task_name'])


class EventQueue:

    prefix = 'queue_task_'

    def __init__(self, queue_names: List[str], connection_pool):
        self.queue_names = queue_names
        self.clean_names = self._clean_queue_names(self.queue_names)
        self.redis = Redis(connection_pool=connection_pool)
        self.event_handlers = {
            EVENT_FINISHED: self.event_finished,
            EVENT_ENQUEUED: self.event_enqueued,
            EVENT_STARTED: self.event_started,
            EVENT_ERROR_TASK: self.event_error,
        }

    def subscribe_to_queues(self, queues: List[str]) -> PubSub:
        pubsub = self.redis.pubsub()
        pubsub.subscribe(queues)
        return pubsub

    def listen(self):
        listener = self.subscribe_to_queues(self.clean_names)
        for event in listener.listen():
            if event['type'] != 'message':
                continue
            channel = event['channel'].decode('utf-8')
            data = json.loads(event['data'].decode('utf-8'))
            logger.debug('Received event from {}: {}'.format(channel, json.dumps({'data': data})))

            self.handle_event(channel, data)

    def handle_event(self, queue_name, event):
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
        return name[len(self.prefix):]

    # Copied from https://github.com/coleifer/huey/blob/1.9.1/huey/storage.py#L302
    def _clean_queue_name(self, name):
        return re.sub('[^a-z0-9]', '', name)

    def _clean_queue_names(self, names: List[str]):
        cleaned = []
        for name in names:
            cleaned.append(self._clean_queue_name(name))
        return cleaned
