""" Publ entry point """

import time
import re
import warnings

import arrow
import flask
import werkzeug.exceptions
from dateutil import tz
from attrdict import AttrDict

from . import rendering, model, index, caching, view, utils, async

DEFAULT_CONFIG = {
    'database': 'sqlite:///:memory:',
    'content_folder': 'content',
    'template_folder': 'templates',
    'static_folder': 'static',
    'static_url_path': '/static',
    'image_output_subdir': '_img',
    'index_rescan_interval': 7200,
    'timezone': tz.tzlocal(),
    'cache': {},
}


class Publ(flask.Flask):
    """ A Publ app; extends Flask so that we can add our own custom decorators and config"""

    def __init__(self, name, config):
        config = AttrDict({**DEFAULT_CONFIG, **config})
        self.publ_config = config

        super().__init__(
            name,
            template_folder=config.template_folder,
            static_folder=config.static_folder,
            static_url_path=config.static_url_path
        )

        self._regex_map = []
        self._last_scan = None

    def path_alias_regex(self, regex):
        """ A decorator that adds a path-alias regular expression; calls
        add_path_regex """
        def decorator(func):
            """ Adds the function to the regular expression alias list """
            self.add_path_regex(regex, func)
        return decorator

    def add_path_regex(self, regex, func):
        """ Add a path-alias regex callback to the request router. Takes the
        following arguments:

        regex -- The regular expression for the path-alias hook
        func -- A function taking a `re.match` object on successful match, and
            returns a tuple of `(url, is_permanent)`; url can be `None` if the
            function decides it should not redirect after all.

        The function may also use `flask.request.args` or the like if it needs
        to make a determination based on query args.
        """
        self._regex_map.append((regex, func))

    def get_path_regex(self, path):
        """ Evaluate the registered path-alias regular expressions """
        for regex, func in self._regex_map:
            match = re.match(regex, path)
            if match:
                return func(match)

        return None, None

    def _start_index(self):
        """ Startup routine for initiating the content indexer """
        model.setup(self.publ_config)
        self._scan_index(True)
        index.background_scan(self.publ_config)

    def _scan_index(self, force=False):
        """ Rescan the index if it's been more than a minute since the last scan """
        now = time.time()
        if (force or not self._last_scan or
                now - self._last_scan > self.publ_config.index_rescan_interval):
            index.scan_index(self.publ_config)
            self._last_scan = now

    def _set_cache_control(self, request):
        if 'CACHE_DEFAULT_TIMEOUT' in self.publ_config.cache:
            request.headers['Cache-Control'] = 'public, max_age={}'.format(
                self.publ_config.cache['CACHE_DEFAULT_TIMEOUT'])


def publ(name, config):

    app = Publ(name, config)

    for route in [
            '/',
            '/<path:category>/',
            '/<template>',
            '/<path:category>/<template>',
    ]:
        app.add_url_rule(route, 'category', rendering.render_category)

    for route in [
            '/<int:entry_id>',
            '/<int:entry_id>-<slug_text>',
            '/<path:category>/<int:entry_id>',
            '/<path:category>/<int:entry_id>-<slug_text>',
    ]:
        app.add_url_rule(route, 'entry', rendering.render_entry)

    app.add_url_rule('/<path:path>.PUBL_PATHALIAS',
                     'path_alias', rendering.render_path_alias)

    app.add_url_rule('/_async/<path:filename>',
                     'async', async.image)

    app.add_url_rule('/_', 'chit', rendering.render_transparent_chit)

    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.register_error_handler(
        werkzeug.exceptions.HTTPException, rendering.render_exception)

    app.jinja_env.globals.update(  # pylint: disable=no-member
        get_view=view.get_view,
        arrow=arrow,
        static=utils.static_url,
        get_template=rendering.get_template
    )

    caching.init_app(app)

    if app.publ_config.index_rescan_interval:
        app.before_request(app._scan_index)

    app.after_request(app._set_cache_control)

    if app.debug:
        # We're in debug mode so we don't want to scan until everything's up
        # and running
        app.before_first_request(app._start_index)
    else:
        # In production, register the exception handler and scan the index
        # immediately
        app.register_error_handler(Exception, rendering.render_exception)
        app._start_index()

    return app
