import logging


logger = logging.getLogger('huey-exporter')

console = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)

logger.addHandler(console)