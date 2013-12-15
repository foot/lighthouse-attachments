#!/usr/bin/env python


import itertools
import json
import shelve
from pprint import pprint as pp

import requests


cache = shelve.open('cache.shelf')

TOKEN = '<YOUR_LIGHTHOUSE_TOKEN>'
URL = 'http://iptego.lighthouseapp.com/'
BASE_PARAMS = {'_token': TOKEN}


def memoize(f):
    def wrap(*args, **kwargs):
        signature = json.dumps((f.__name__, args, kwargs))
        if signature not in cache:
            result = f(*args, **kwargs)
            cache[signature] = result
        return cache[signature]
    return wrap


@memoize
def _get(*args, **kwargs):
    response_text = requests.get(*args, **kwargs).text
    return json.loads(response_text)


def get_projects():
    res = _get(URL + 'projects.json', params=BASE_PARAMS)
    return (p['project'] for p in res['projects'])


def get_tickets(project_id):

    # seems to be the max limit
    limit = 100

    def page(number):
        params = dict(q="sort:number", page=number, limit=limit, **BASE_PARAMS)
        res = _get(URL + 'projects/' + str(project_id) + '/tickets.json',
                   params=params)
        return res['tickets']

    n = 1
    there_is_another_page = True
    while there_is_another_page:
        tickets = page(n)

        for ticket in tickets:
            yield ticket['ticket']

        n += 1
        there_is_another_page = len(tickets) == limit


def get_ticket(project_id, number):
    res = _get(URL + 'projects/' + str(project_id) + '/tickets/' +
               str(number) + '.json', params=BASE_PARAMS)
    return res['ticket']


def get_attachments(project_id):

    tickets_with_attachments = (
        get_ticket(project_id, t['number'])
        for t in get_tickets(project_id)
        if t['attachments_count'] > 0
    )

    for ticket in tickets_with_attachments:
        for a in ticket['attachments']:
            attachment = a.get('attachment') or a.get('image')
            attachment['ticket_id'] = ticket['number']
            yield attachment


def take(n, generator):
    return list(itertools.islice(generator, 0, n))


def summary(project_id):

    print "Tickets about bad things:"
    about_bad_things = {
        t['number']: t['title'] for t in get_tickets(project_id)
        if "bad" in t['title'].lower()
    }
    pp(about_bad_things)

    print "\nAttachments by type:"
    attachments = get_attachments(project_id)
    key = lambda a: a.get('filename').split('.')[-1]
    types = [
        (name, len(list(group)))
        for name, group in itertools.groupby(sorted(attachments, key=key), key)
    ]
    top_10 = sorted(types, key=lambda p: p[1], reverse=True)[:10]
    pp(top_10)


if __name__ == '__main__':

    import sys

    projects = get_projects()

    if len(sys.argv) > 1:
        name = sys.argv[1]
        projects = (p for p in projects if p['name'] == name)

    project_id = list(projects)[0]['id']

    summary(project_id)
