# Huey Prometheus Exporter
This project provides metrics about the [huey task queue](https://github.com/coleifer/huey) for prometheus.

Latest Version: **1.0.1**


---
##### Important

- If you use `huey 1.x` then install `huey-exporter 0.2.2`. Checkout the git tag [0.2.2](https://github.com/APGSGA/huey-exporter/tree/0.2.2).
- If you use `huey 2.x` then install `huey-exporter >= 1.0`.

---

### Requirements

- [Huey](https://github.com/coleifer/huey)
- [Hueyx](https://github.com/APGSGA/hueyx)

## Usage

#### Installation
Installation of the latest release:
```
pip install git+https://github.com/APGSGA/huey-exporter.git@1.0.0
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
[Image on dockerhub](https://hub.docker.com/r/apgsga/huey-exporter/)

The usage is the same as the non-docker.

Example:
```
docker run -e REDIS_CONNECTION_STRING=redis://somehost:6379/0 apgsga/huey-exporter
```

## Exposed Metrics
- `hueyx_signals`

Labels: `'queue_name', 'task_name', 'signal', 'hueyx_environment'`.

- `hueyx_queue_task_count`

Labels: `'queue_name', 'task_name'`

---

### Internals

huey-exporter consists of two modules which work completely independent of each other.

#### Signal listener

The signal listener subscribes to the hueyx `hueyx.huey2.signaling` pubsub. Everytime [hueyx](https://github.com/APGSGA/hueyx) 
receives a [huey signal](https://huey.readthedocs.io/en/latest/signals.html)
the exporter receives it and increases the according prometheus counter.

#### Queue length
The second exporter module is the queue_length counter. The counter first tries to find huey queues on redis by
watching all redis keys with the pattern `huey.redis.*`. The key only exists if the queue contains at least one element
so it can take some time.
The counter reads all tasks then and reports them to prometheus.
