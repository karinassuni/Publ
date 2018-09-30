# webmention.py
""" Mechanism for sending all webmentions for an entry """

import concurrent.futures
import logging
from html.parser import HTMLParser
import datetime
import urllib.parse

from flask import current_app as app
import ronkyuu.webmention

from . import model, index, background
from pony import orm

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class URLScanner(HTMLParser):
    """ A utility class to return all of the linked URLs, deduplicated """

    def __init__(self, base_url):
        super().__init__()

        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.urls = set()

        self.base_url = base_url

    def handle_starttag(self, tag, attributes):
        if tag.lower() == 'a':
            for href in [val for attr, val in attributes
                         if attr.lower() == 'href']:
                self.urls.add(urllib.parse.urljoin(self.base_url, href))

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def error(self, message):
        return message


def send_pings(entry):
    """ Schedule sending the pings for an entry """

    permalink = entry.permalink(absolute=True, expand=True)

    url_scanner = URLScanner(permalink)
    for html in (entry.body(absolute=True, count=0),
                 entry.more(absolute=True, count=0)):
        url_scanner.feed(html)

    logger.info("%d: found %d URLs", entry.id, len(url_scanner.urls))
    for url in url_scanner.urls:
        logger.info("%d: %s -> %s", entry.id, permalink, url)
        background.submit(send_ping, entry, permalink, url)


def send_ping(entry, entry_permalink, url):
    """ Send the ping to the remote site """

    logger.info("Sending ping for entry %d: %s -> %s",
                entry.id, entry_permalink, url)

    now = datetime.datetime.now()

    if app.debug:
        # don't actually send webmentions in debug mode
        response = None
    else:
        response = ronkyuu.webmension.sendWebmention(entry_permalink, url)

    with orm.db_session():
        log_entry = model.WebMentionSent(
            entry=model.Entry.get(id=entry.id),
            target=url,
            success=response is not None and 200 <= response.status_code < 300,
            status_code=response and response.status_code)

    if response:
        logger.info("%s: Got response: %d", url, response.status_code)
    else:
        logger.info("%s: endpoint not found", url)

    orm.commit()
