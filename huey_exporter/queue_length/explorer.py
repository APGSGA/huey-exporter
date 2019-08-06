import pickle
from typing import List, Dict, Set

from redis import ConnectionPool, Redis
import time


class HueyQueue:
    _key_prefix = 'huey.redis.'

    def __init__(self, redis_key: str, redis: Redis):
        self.redis: Redis = redis
        self.redis_key = redis_key

    @property
    def name(self) -> str:
        return self.redis_key.replace(self._key_prefix, '')

    def __str__(self):
        return f'<{self.redis_key}>'

    def __eq__(self, other):
        return self.redis_key == other.redis_key

    def __hash__(self):
        return hash(self.redis_key)

    def __len__(self):
        return self.redis.llen(self.redis_key)

    @property
    def tasks(self) -> Dict[str, int]:
        task_dict = {}
        elements = self.redis.lrange(self.redis_key, 0, 0)
        for element in elements:
            message = pickle.loads(element)
            if message.name not in task_dict:
                task_dict[message.name] = 0
            task_dict[message.name] += 1
        return task_dict


class HueyExplorer:
    """
    Returns the given huey queues on redis.
    """
    _key_prefix = 'huey.redis.'

    def __init__(self, pool: ConnectionPool, queue_cache_time=60):
        """
        :param pool:
        :param queue_cache_time: cache time of queues in seconds.
        """
        self.redis = Redis(connection_pool=pool)
        self._cache = ExpiringCache(queue_cache_time)

    def _list_huey_keys(self) -> List:
        byte_keys = self.redis.keys(self._key_prefix + '*')
        return [key.decode('utf-8') for key in byte_keys]

    @property
    def queues(self) -> Set[HueyQueue]:
        return set([HueyQueue(key, self.redis) for key in self._list_huey_keys()])

    @property
    def cached_queues(self) -> Set[HueyQueue]:
        """
        Redis removes keys with size 0. Therefore we cache the queues so we can still report queue size zero.
        :return:
        """
        for queue in self.queues:
            self._cache.add(queue)
        queues = self._cache.get()
        return queues


class ExpiringCache:
    """
    Class which caches objects for a certain amount of seconds.
    """
    def __init__(self, expiring_in=60*10):
        self.expiring_in = expiring_in
        self.cache_dict: Dict[HueyQueue, int] = {}

    @property
    def _current_second(self):
        return int(time.time())

    def add(self, element: HueyQueue):
        self.cache_dict[element] = self._current_second

    def clear_cache(self):
        to_clearing_keys = []
        for key, value in self.cache_dict.items():
            if value < self._current_second - self.expiring_in:
                to_clearing_keys.append(key)

        for key in to_clearing_keys:
            del self.cache_dict[key]

    def get(self) -> Set[HueyQueue]:
        self.clear_cache()
        return set(self.cache_dict.keys())



