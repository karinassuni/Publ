# background.py
""" Support stuff for running background tasks """

import concurrent.futures
import logging

from . import config

app = None  # pyint: disable=invalid-name

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def threadpool():
    if not threadpool.pool:
        logger.info("Initializing threadpool")
        threadpool.pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.max_worker_threads,
            thread_name_prefix="Background")
    return threadpool.pool
threadpool.pool = None


def submit(fn, *args, **kwargs):
    threadpool().submit(_context_runner, fn, *args, **kwargs)


def _context_runner(fn, *args, **kwargs):
    logger.debug("running task %s %s %s", fn, args, kwargs)
    try:
        with app.app_context():
            fn(*args, **kwargs)
    except:  # pylint: disable=broad-except
        logger.exception("Got exception")
