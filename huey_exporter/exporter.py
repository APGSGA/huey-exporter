import click
import redis
from prometheus_client import start_http_server

from huey_exporter.EventListener import EventListener
from huey_exporter.exporter_logging import logger





@click.command()
@click.option('--connection-string', '-c',
              envvar='REDIS_CONNECTION_STRING',
              default='redis://localhost:6379',
              help='Connection string to redis including database. for example redis://localhost:6379/0'
              )
@click.option('--port', '-p',
              envvar='EXPORTER_PORT',
              default=9100,
              type=click.IntRange(0, 65535),
              help='Port to expose the metrics on'
              )
@click.option('--logging-level', '-l',
              envvar='LOGGING_LEVEL',
              default='INFO',
              help='Set the logging level of the huey-exporter'
              )
def run_exporter(connection_string, port, logging_level):
    logger.setLevel(logging_level)

    # Start up the server to expose the metrics.
    start_http_server(port)
    connection_pool = redis.BlockingConnectionPool.from_url(
            connection_string,
            max_connections=5,
            timeout=10
    )

    queue = EventListener(connection_pool)
    queue.listen()


def main():
    run_exporter()

if __name__ == '__main__':
    run_exporter()
