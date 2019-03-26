import asyncio
import datetime
import json
import time
import os

from aiohttp import web
from file_read_backwards import FileReadBackwards

file_name = '/var/log/apt/history.log'
cache = None


def check_cache():
    """
    Compares the size and last modified date of the file with the same
    data stored in the cache. If they match, returns data from the
    cache, otherwise None

    """
    if cache is None:
        return None
    stat = os.stat(file_name)
    if cache['stat']['size'] != stat.st_size or cache['stat']['atime'] != stat.st_atime:
        return None
    return cache['data']


def update_cache(data):
    """
    Saves up-to-date data to the cache along with the last modified
    date and size of the file. Gets son object of type
    {"start_time": ... , "end_time": ...}
    """
    stat = os.stat(file_name)
    global cache
    cache = {'stat': {'size': stat.st_size,
                      'atime': stat.st_atime},
             'data': data}


def get_data():
    """
    Takes data from cache if possible, else reads file
    /var/log/apt/history.log in reverse order using the
    file_read_backwards library. Using the file structure reads one
    block at a time and, if this is a system update, saves in the cache
    the unix time of the beginning and the ending as json object of
    type {"start_time": ... , "end_time": ...} and returns it

    """
    cache_data = check_cache()
    if cache_data is not None:
        return cache_data
    time.sleep(5)
    with FileReadBackwards(file_name, 'utf-8') as file:
        update_time = None
        while True:
            block = read_block(file)
            if not block:
                break
            update_time = process_block(block)
            if update_time is not None:
                break
    if update_time is None:
        result = json.dumps({'error': 'can not get information about last system update'})
    else:
        result = json.dumps({'start_time': update_time['start'],
                             'end_time': update_time['end']})
        update_cache(result)

    return result


def read_block(frb):
    """
    Reads one of the blocks separated by empty lines and return data as
    a dict. Receive frb as FileReadBackwards

    """
    res = {}
    while True:
        line = frb.readline().split()
        if not line:
            break
        tag = line[0]
        res[tag] = line[1::]
    return res


def process_block(block):
    """
    Checks the logged command and if it's a system update, returns the
    time in the correct format

    """
    com_line = block['Commandline:']
    com_line = [x for x in com_line if not x.startswith('-')]  # discards the command-line options
    if com_line[0] != 'apt-get' or (com_line[1] != 'upgrade' and com_line[1] != 'dist-upgrade'):
        return None
    start_time = block['Start-Date:']
    end_time = block['End-Date:']
    result = {'start': parse_time(start_time),
              'end': parse_time(end_time)}
    return result


def parse_time(time_str):
    """
    parses the time from a string in the format ['%Y-%m-%d', '%H:%M:%S']
    to unix time as int

    """
    time_str = '%s %s' % (time_str[0], time_str[1])
    time_str = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S').timestamp()
    return int(time_str)


async def get_upgrade_time(request):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, get_data)
    return web.Response(text=data)


app = web.Application()
app.router.add_route('GET', '/last-upgrade', get_upgrade_time)
web.run_app(app)
