# webmention.py
""" Mechanism for sending all webmentions for an entry """

import concurrent.futures
import logging
from html.parser import HTMLParser
import datetime

from flask import current_app as app
import ronkyuu.webmention

from . import model, index
from pony import orm

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class URLScanner(HTMLParser):
    """ A utility class to return all of the linked URLs, deduplicated """

    def __init__(self):
        super().__init__()

        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.urls = set()

    def handle_starttag(self, tag, attributes):
        if tag == 'a' and 'href' in attributes:
            self.urls.add(attributes['href'])

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)

    def error(self, message):
        return message


def send_pings(entry):
    """ Schedule sending the pings for an entry """

    record = entry.record
    permalink = entry.permalink(absolute=True, expand=True)

    url_scanner = URLScanner()
    for html in (entry.body(absolute=True, count=0),
                 entry.more(absolute=True, count=0)):
        url_scanner.feed(html)

    for url in url_scanner.urls:
        index.THREAD_POOL.submit(send_ping, record.id, permalink, url)


@orm.db_session
def send_ping(entry_id, entry_permalink, url):
    """ Send the ping to the remote site """

    logger.info("Sending ping for entry %d: %s -> %s",
                entry_id, entry_permalink, url)

    if app.debug:
        # don't actually send pings in debug mode
        return

    response = ronkyuu.webmension.sendWebmention(entry_permalink, url)

    log_entry = model.WebmentionSent(entry=model.Entry.get(id=entry.id),
                                     target=url,
                                     success=response and 200 <= response.status_code < 300,
                                     status_code=response and response.status_code)

    if response:
        logger.info("%s: Got response: %d", url, response.status_code)
    else:
        logger.info("%s: endpoint not found", url)

    orm.commit()
