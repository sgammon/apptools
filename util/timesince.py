# -*- coding: utf-8 -*-

'''

Util: Timesince

Takes two datetime objects and returns the time between d and now
as a nicely formatted string, e.g. "10 minutes".  If d occurs after now,
then "0 minutes" is returned.

Units used are years, months, weeks, days, hours, and minutes.
Seconds and microseconds are ignored.  Up to two adjacent units will be
displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

Adapted from [http://blog.natbat.co.uk/archive/2003/Jun/14/time_since](http://blog.natbat.co.uk/archive/2003/Jun/14/time_since)

'''

import datetime


def getword(singular, plural, n):

    if n == 1:
        return singular
    else:
        return plural


def timesince(d, now=None):
    chunks = (
      (60 * 60 * 24 * 365, lambda n: getword('year', 'years', n)),
      (60 * 60 * 24 * 30, lambda n: getword('month', 'months', n)),
      (60 * 60 * 24 * 7, lambda n: getword('week', 'weeks', n)),
      (60 * 60 * 24, lambda n: getword('day', 'days', n)),
      (60 * 60, lambda n: getword('hour', 'hours', n)),
      (60, lambda n: getword('minute', 'minutes', n))
    )
    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.datetime.now()

    # ignore microsecond part of 'd' since we removed it from 'now'
    delta = now - (d - datetime.timedelta(0, 0, d.microsecond))
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return u'0 ' + 'minutes'
    for i, (seconds, name) in enumerate(chunks):
        count = since // seconds
        if count != 0:
            break

    s = '%(number)d %(type)s' % {'number': count, 'type': name(count)}
#     if i + 1 < len(chunks):
#         # Now get the second item
#         seconds2, name2 = chunks[i + 1]
#         count2 = (since - (seconds * count)) // seconds2
#         if count2 != 0:
#             s += ', %(number)d %(type)s' % {'number': count2, 'type': name2(count2)}
    return s + ' ago'
