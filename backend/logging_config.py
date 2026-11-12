from __future__ import annotations

import logging
import sys

from config import get_config

_CONFIG = get_config()

logging.basicConfig(
    level=getattr(logging, _CONFIG.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)

logger = logging.getLogger("biomed_ai")
