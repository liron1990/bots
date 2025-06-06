import logging

logger = logging.getLogger("tor4you")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TID:%(thread)d] %(message)s"
)