#!/usr/bin/env python
import logging
from scoro2clearbooks.utils import run_sync

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger("sync")
logging.basicConfig(format=FORMAT, level=logging.INFO)

errors = run_sync()

if len(errors) == 0:
    logger.info("Complete")
else:
    messages = ""
    for e in errors:
        messages += "INV{}: {}\n".format(e["invoice"], e["error"])
    logger.info("Complete with {} errors\n{}".format(len(errors), messages))
