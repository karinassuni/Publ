# config.py
""" configuration container for Publ.

The following configuration options are supported:

database_config -- the configuration sent along to PonyORM to configure the
    index storage. See https://docs.ponyorm.com/firststeps.html#database-binding
    for more information. Defaults to in-memory SQLite.

content_folder -- the folder that stores content files (images, entries,
    category metadata, etc.). Defaults to "content"

template_folder -- the folder that stores render templates. Defaults to
    "templates"

static_folder -- the folder that stores static assets. Defaults to "static"

static_url_path -- the path mapping for static assets. Defaults to "/static"

image_output_subdir -- the subdirectory of static_folder where image renditions
    will be kept. Defaults to "_img"

index_rescan_interval -- how often to rescan the content index for changes.
    Defaults to 7200 (2 hours)

image_cache_interval -- how often to scan the image rendition cache for expired
    content. Defaults to 3600 (1 hour)

image_cache_age -- maximum age of images in the rendition cache. Defaults to
    86400*7 (one week).

timezone -- the default timezone to use for new entries. Defaults to tz.tzlocal()

cache -- Flask-Caching's configuration. See
    https://pythonhosted.org/Flask-Caching/#configuring-flask-caching
    for more information. Defaults to no cache.

max_worker_threads -- the maximum number of worker threads to launch for
    background tasks (image renditions, etc.). Defaults to None, which sets a
    default value based on the number of processors in the server.

max_index_threads -- the maximum number of worker threads to launch for the
    content indexer. Defaults to 4.


 """

import sys
from dateutil import tz

# pylint: disable=invalid-name

database_config = {
    'provider': 'sqlite',
    'filename': ':memory:'
}

content_folder = 'content'
template_folder = 'templates'
static_folder = 'static'
static_url_path = '/static'
image_output_subdir = '_img'
index_rescan_interval = 7200
image_cache_interval = 3600
image_cache_age = 86400 * 7  # one week
entry_publish_interval = 60
timezone = tz.tzlocal()
cache = {}
max_worker_threads = None
max_index_threads = 4


def setup(cfg):
    """ set up the global configuration from an object """

    # copy the necessary configuration values over
    this_module = sys.modules[__name__]
    for name, value in cfg.items():
        if hasattr(this_module, name):
            setattr(this_module, name, value)
