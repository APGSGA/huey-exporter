from typing import List, Dict, Set

from redis import ConnectionPool, Redis
import time


class HueyQueue:
    def __init__(self, name: str, redis: Redis):
        self.redis: Redis = redis
        self.name = name

    def __str__(self):
        return f'<{self.name}>'

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return self.redis.llen(self.name)


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
        return self._cache.get()


class ExpiringCache:
    """
    Class which caches objects for a certain amount of seconds.
    """
    def __init__(self, expiring_in=60):
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



