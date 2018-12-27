# Huey Prometheus Exporter
This project provides metrics about the [huey task queue](https://github.com/coleifer/huey) for prometheus.

Latest Version: **0.2.0**

## Usage

#### Installation
Installation of the latest release:
```
pip install git+https://github.com/APGSGA/huey-exporter.git@0.2.0
```
Installation of the master branch:
```
pip install git+https://github.com/APGSGA/huey-exporter.git@master
```

The command `huey_exporter` will start a webserver (default port 9100) and serves the metrics.

The exporter will explore the Redis instance and therefore find the huey queue names by themself.  

#### Running
```
Usage: huey_exporter [OPTIONS]

Options:
  -c, --connection-string TEXT  Connection string to redis including database.
                                for example redis://localhost:6379/0
  -p, --port TEXT               Port to expose the metrics on.
  --logging-level               Logging level of the exporter. Default is INFO.
                                DEBUG | INFO | WARNING | ERROR
  --help                        Show this message and exit.

```

Example:
```
huey_exporter
```
The huey_exporter can also be configured by the environment variables `REDIS_CONNECTION_STRING`, `LOGGING_LEVEL` and `EXPORTER_PORT`
### Docker
[Image on dockerhub](https://hub.docker.com/r/mglauser/huey-exporter/)

The usage is the same as the non-docker.

Example:
```
docker run -e REDIS_CONNECTION_STRING=redis://somehost:6379/0 sebu/huey-exporter
```

## Exposed Metrics
All metrics have the labels *task name* and *queue name* attached.
#### huey_enqueued_tasks (Requires RedisEnqueuedEventHuey)
Counter
#### huey_started_tasks
Counter

#### huey_finished_tasks
Counter

#### huey_error_tasks
Counter

#### huey_task_duration_seconds
Summary

### Example
Tasks started per Minute:
```
sum by (queue_name) (increase(huey_started_tasks[1m]))
```

Task Queue Length:
```
sum by (queue_name) (huey_enqueued_tasks - huey_started_tasks)
```

Average Task duration:
```
rate(huey_task_duration_seconds_sum[5m])/rate(huey_task_duration_seconds_count[5m])
```

## RedisEnqueuedEventHuey
Because huey only emits events from the consumer or scheduler, the event `huey_enqueued_tasks` is not supported natively.

But it's easy to add. huey-exporter offers a thin wrapper around RedisHuey that enables this functionality.
You first you need to install huey-exporter in your project.
And then either use it, as you would normally.
```
from huey_exporter import RedisEnqueuedEventHuey
RedisEnqueuedEventHuey()
```
Or if you're using django set the backend_class to the following
```
'backend_class': 'huey_exporter.RedisEnqueuedEventHuey',
```
