import logging
import sys
import warnings

from colorlog import ColoredFormatter

warnings.filterwarnings("ignore")


LOGFORMAT = (
    "%(asctime)s %(log_color)s [%(levelname)s] %(log_color)s%(message)s%(reset)s"
)
LOG_COLORS = {
    "DEBUG": "white",
    "INFO": "white",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}


formatter = ColoredFormatter(LOGFORMAT, log_colors=LOG_COLORS, datefmt="%d-%b %H:%M")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger = logging.getLogger("TeslaLog")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
