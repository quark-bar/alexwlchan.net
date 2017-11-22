#!/usr/bin/env python
# -*- encoding: utf-8
"""
Print a summary of analytics from my website.

Usage: reports.py [options]

Options:
  --days=<COUNT>        Number of days of records to analyse.
  --day=<DAY>           Day to analyse.
  --month=<MONTH>       Month to analyse.
  --year=<YEAR>         Year to analyse.
  --limit=<LIMIT>       Max number of records to show.
  --no-paths            Don't print a complete record of paths by IP.

"""

from collections import Counter
import datetime
from urllib.parse import parse_qs, urlparse

import docopt
from peewee import fn

from analytics import database, PageView


def get_query(start, end):
    query = PageView.select()
    if start and end:
        query = query.where(PageView.timestamp.between(start, end))
    elif start:
        query = query.where(PageView.timestamp >= start)
    elif end:
        query = query.where(PageView.timestamp <= end)
    return query


def page_views(query):
    return query.count()


def unique_ips(query):
    return (query
            .select(PageView.ip)
            .group_by(PageView.ip)
            .count())


def top_pages(query, limit):
    return (query
            .select(PageView.title, fn.COUNT(PageView.id))
            .group_by(PageView.title)
            .order_by(fn.COUNT(PageView.id).desc())
            .tuples()
            .limit(limit))


def top_traffic_times(query):
    chunks = 3
    hour = fn.date_part('hour', PageView.timestamp) / chunks
    id_count = fn.COUNT(PageView.id)
    result = dict(query
                  .select(hour, id_count)
                  .group_by(hour)
                  .order_by(hour)
                  .tuples())
    total = sum(result.values())
    return [
        (
            '%s - %s' % (i * chunks, (i + 1) * chunks),
            result.get(i, 0),
            (100. * result.get(i, 0)) / total
        )
        for i in range(int(24 / chunks))]


def user_agents(query, limit):
    c = Counter(pv.headers.get('User-Agent') for pv in query)
    return c.most_common(limit)


def languages(query, limit):
    c = Counter(pv.headers.get('Accept-Language') for pv in query)
    return c.most_common(limit)


def _normalise_referrer(referrer):
    parts = urlparse(referrer)

    if parts.netloc.startswith(('www.google.', 'encrypted.google.')):
        qs = parse_qs(parts.query)
        try:
            return f'Google ({qs["q"][0]})'
        except KeyError:
            return 'Google'

    if parts.netloc == 'alexwlchan.net':
        return None

    tco_urls = {
        'https://t.co/6R9gyKJfqu': 'https://twitter.com/alexwlchan/status/928389714998104065',
    }

    if parts.netloc == 't.co':
        for u, v in tco_urls.items():
            if referrer.startswith(u):
                return v

    aliases = {
        'https://www.bing.com/': 'Bing',
        'https://duckduckgo.com/': 'DuckDuckGo',
    }

    return aliases.get(referrer, referrer)


def get_referrers(query, limit):
    c = Counter(_normalise_referrer(pv.referrer) or None for pv in query)
    return c.most_common(limit)


def get_paths(query, limit):
    inner = (query
             .select(PageView.ip, PageView.url)
             .order_by(PageView.timestamp))
    paths = (PageView
             .select(
                 PageView.ip,
                 fn.GROUP_CONCAT(PageView.url))
             .from_(inner.alias('t1'))
             .group_by(PageView.ip)
             .order_by(fn.COUNT(PageView.url).desc())
             .tuples()
             .limit(limit))
    return [(ip, urls.split(',')) for ip, urls in paths]


def get_low_high(query):
    base = query.select(PageView.timestamp)

    def conv(s):
        return datetime.datetime.strptime(
            s, '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M')

    low = base.order_by(PageView.id.asc()).scalar()
    high = base.order_by(PageView.id.desc()).scalar()
    return conv(low), conv(high)


def print_banner(s):
    print('')
    print('-' * len(s))
    print(s)
    print('-' * len(s))


def run_report(start, end, limit, skip_paths=False):
    query = get_query(start, end)
    low, high = get_low_high(query)

    print_banner(f'Overview from {low} to {high}')
    print(f'{page_views(query):#4d} page views')
    print(f'{unique_ips(query):#4d} unique IPs')

    print_banner('Top Pages')
    for title, count in top_pages(query, limit):
        print(f'{count:#4d} : {title}')

    print_banner('Traffic by Hour')
    for hour, count, percent in top_traffic_times(query):
        print('%9s : %s (%s%%)' % (hour, count, round(percent, 1)))

    if not skip_paths:
        print_banner('Paths')
        for ip, path in get_paths(query, limit):
            print(ip)
            for url in path:
                print(f' * {url}')

    print_banner('Referrers')
    for referrer, count in get_referrers(query, limit):
        print(f'{count:#4d} : {referrer}')


if __name__ == '__main__':
    args = docopt.docopt(__doc__)

    database.connect()

    today = datetime.date.today()
    if args['--year'] or args['--month'] or args['--day']:
        start_date = datetime.date(today.year, 1, 1)
        if args['--year']:
            start_date = start_date.replace(year=args['--year'])
        if args['--month']:
            start_date = start_date.replace(month=args['--month'])
        if args['--day']:
            start_date = start_date.replace(day=args['--day'])
    else:
        start_date = None

    end_date = None
    if args['--limit']:
        delta = datetime.timedelta(days=int(args['--limit']))
        if start_date:
            end_date = start_date + delta
        else:
            start_date = today - delta

    run_report(start_date, end_date, int(args['--limit']), args['--no-paths'])
    database.close()