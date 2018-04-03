# view.py
# A view of entries

from . import model, utils
from .entry import Entry
import arrow

'''
TODO: figure out the actual API

expected view specs:

limit - number of entries to limit to
category - top-level category to retrieve
recurse - whether to recurse into subcategories
date - date spec for the view, one of:
    YYYY - just the year
    YYYYMM - year and month
    YYYYMMDD - year/month/day
    YYYY_WW - year/week
start_entry - the first entry to show (in the sort order)
last_entry - the last entry to show (in the sort order)
prev_entry - show entries after this one (in the sort order)
next_entry - show entries prior to this one (in the sort order)
sort - sorting spec, at the very least:
    newest
    oldest
    title
future - whether to show entries from the future
'''

class View:
    def __init__(self, spec=None):
        self.spec = spec or {}
        for k,v in spec.items():
            print("{}='{}'".format(k,v))

        # primarily restrict by publication status
        if self.spec.get('future', False):
            where = (
                (model.Entry.status == PublishStatus.PUBLISHED) |
                (model.Entry.status == PublishStatus.SCHEDULED)
            )
        else:
            where = (
                (model.Entry.status == model.PublishStatus.PUBLISHED) |
                (
                    (model.Entry.status == model.PublishStatus.SCHEDULED) &
                    (model.Entry.entry_date < arrow.now().datetime)
                )
            )

        # # restrict by category
        if 'category' in self.spec:
            cat_where = (model.Entry.category == self.spec['category'])
            if self.spec.get('recurse', False):
                cat_where = cat_where | (model.Entry.category % (self.spec['category'] + '/%'))
            where = where & cat_where

        # TODO sorting
        self.query = model.Entry.select().where(where)
        print(self.query.sql())

    def __getattr__(self, name):
        if name == 'entries':
            return [Entry(e) for e in self.query]

    def where(self, **restrict):
        return View({**self.spec, **restrict})

def get_view(**kwargs):
    return View(spec=kwargs)
