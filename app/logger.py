import logging

logging.basicConfig(
    filename="log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

logger = logging.getLogger("my_logs")
