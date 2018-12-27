from typing import List, Dict, Set

from redis import ConnectionPool, Redis
import time


class RedisExplorer:
    """
    Returns the given huey queues on redis.
    """
    _key_prefix = 'huey.redis.'

    def __init__(self, pool: ConnectionPool):
        self.redis = Redis(connection_pool=pool)

    def list_huey_keys(self) -> List:
        return self.redis.keys(self._key_prefix + '*')

    @property
    def queue_names(self) -> List[str]:
        queue_names = []
        keys = self.list_huey_keys()
        for key in keys:
            decoded_key: str = key.decode('utf-8')
            queue_name = decoded_key.replace(self._key_prefix, '')
            queue_names.append(queue_name)
        return queue_names


class ExpiringCache:
    def __init__(self, expiring_in=60):
        self.expiring_in = expiring_in
        self.cache_dict: Dict[str, int] = {}

    @property
    def _current_second(self):
        return int(time.time())

    def add(self, element):
        self.cache_dict[element] = self._current_second

    def clear_cache(self):
        to_clearing_keys = []
        for key, value in self.cache_dict.items():
            if value < self._current_second - self.expiring_in:
                to_clearing_keys.append(key)

        for key in to_clearing_keys:
            del self.cache_dict[key]

    def get(self) -> Set[str]:
        self.clear_cache()
        return set(self.cache_dict.keys())


class CachedRedisExplorer(RedisExplorer):

    def __init__(self, pool: ConnectionPool, expiring_in=60):
        """
        Redis queue explorer which caches the keys for 60 seconds
        :param pool:
        :param expiring_in:
        """
        super().__init__(pool)
        self.cache = ExpiringCache(expiring_in)

    @property
    def queue_names(self) -> Set[str]:
        uncached_names = super().queue_names
        for name in uncached_names:
            self.cache.add(name)
        return self.cache.get()
