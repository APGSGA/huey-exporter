from prometheus_client import Counter
from redis.client import Redis

from huey_exporter.exporter_logging import logger
import json

# Create a metric to track time spent and requests made.
COUNTER = Counter('hueyx_signals', 'Huey task signals', ['queue_name', 'task_name', 'signal', 'hueyx_environment'])


class EventListener:
    QUEUE_NAME = 'hueyx.huey2.signaling'

    def __init__(self, connection_pool):
        self.connection_pool = connection_pool
        self.redis = Redis(connection_pool=connection_pool)
        self.pubsub = self.redis.pubsub()

    def listen(self):
        """
        Listens to the queue.
        :return:
        """
        self.pubsub.subscribe(self.QUEUE_NAME)
        logger.info(f'Subscribed to {self.QUEUE_NAME}')
        while True:
            message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=0.3)
            if message:
                if message['type'] != 'message':
                    continue
                data = json.loads(message['data'].decode('utf-8'))
                self.handle_event(data)

    def handle_event(self, data: {}):
        try:
            COUNTER.labels(data['queue'], data['task'], data['signal'], data['environment']).inc()

        except KeyError:
            logger.debug(f'Ignored event {data}')
