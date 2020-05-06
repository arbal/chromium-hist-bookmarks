#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import codecs
import json
import os
import shutil
import sqlite3
import sys
from typing import Union
from unicodedata import normalize

from Alfred3 import Items as Items
from Alfred3 import Tools as Tools

# Bookmark file path relative to HOME
BOOKMARKS = [
    '/Library/Application Support/Chromium/Default/Bookmarks',
    '/Library/Application Support/BraveSoftware/Brave-Browser/Default/Bookmarks',
    '/Library/Application Support/BraveSoftware/Brave-Browser-Dev/Default/Bookmarks',
    '/Library/Application Support/Google/Chrome/Default/Bookmarks',
    '/Library/Application Support/Vivaldi/Default/Bookmarks',
    '/Library/Application Support/com.operasoftware.Opera/Bookmarks'
]

FIRE_BOOKMARKS = '/Library/Application Support/Firefox/Profiles'


def removeDuplicates(li: list) -> list:
    """
    Removes Duplicates from history file

    Args:
        li (list): list of history entries

    Returns:
        list: filtered history entries
    """
    newList = list()
    for i in li:
        if i not in newList:
            newList.append(i)
    return newList


def get_all_urls(the_json: str) -> list:
    """
    Extract all URLs and title from Bookmark files

    Args:
        the_json (str): All Bookmarks read from file

    Returns:
        list(tuble): List of tublle with Bookmarks url and title
    """
    def extract_data(data: dict):
        if isinstance(data, dict) and data.get('type') == 'url':
            urls.append({'name': data.get('name'), 'url': data.get('url')})
        if isinstance(data, dict) and data.get('type') == 'folder':
            the_children = data.get('children')
            get_container(the_children)

    def get_container(o: Union[list, dict]):
        if isinstance(o, list):
            for i in o:
                extract_data(i)
        if isinstance(o, dict):
            for k, i in o.items():
                extract_data(i)

    urls = list()
    get_container(the_json)
    s_list_dict = sorted(urls, key=lambda k: k['name'], reverse=False)
    ret_list = [(l.get('name'), l.get('url')) for l in s_list_dict]
    return ret_list


def paths_to_bookmarks() -> list:
    """
    Get all valid bookmarks pahts from BOOKMARKS

    Returns:
        list: valid bookmark paths
    """
    user_dir = os.path.expanduser('~')
    bms = [f"{user_dir}{p}" for p in BOOKMARKS]
    valid_bms = list()
    for b in bms:
        if os.path.isfile(b):
            valid_bms.append(b)
    return valid_bms


def path_to_fire_bookmarks() -> str:
    """
    Get valid pathes to firefox history from BOOKMARKS variable

    Returns:
        list: available paths of history files
    """
    user_dir = os.path.expanduser('~')
    f_home = f"{user_dir}{FIRE_BOOKMARKS}"
    if not os.path.isdir(f_home):
        return None
    f_home_dirs = [f'{f_home}/{o}' for o in os.listdir(f_home)]
    valid_hist = None
    for f in f_home_dirs:
        if os.path.isdir(f):
            f_sub_dirs = [f'{f}/{o}' for o in os.listdir(f)]
            for fs in f_sub_dirs:
                if os.path.isfile(fs) and os.path.basename(fs) == 'places.sqlite':
                    valid_hist = fs
    return valid_hist


def load_fire_bookmarks(fire_locked_db: str) -> list:
    """
    Load Firefox History files into list

    Args:
        fire_locked_db (list): Contains valid history paths

    Returns:
        list: hitory entries unfiltered
    """
    fire_history_db = '/tmp/places.sqlite'
    results = list()
    try:
        shutil.copy2(fire_locked_db, '/tmp')
        with sqlite3.connect(fire_history_db) as c:
            cursor = c.cursor()
            select_statement = """
            SELECT b.title, h.url
            FROM moz_places h, moz_bookmarks b
            WHERE h.id = b.fk
            """
            cursor.execute(select_statement)
            r = cursor.fetchall()
            results.extend(r)
        os.remove(fire_history_db)
    except sqlite3.Error:
        pass
    return [ret for ret in results if r[0] is not None] if len(results) > 0 else list()


def get_json_from_file(file: str) -> json:
    """
    Get Bookmark JSON

    Args:
        file(str): File path to valid bookmark file

    Returns:
        str: JSON of Bookmarks
    """
    return json.load(codecs.open(file, 'r', 'utf-8-sig'))['roots']


def match(search_term: str, results: list) -> list:
    search_terms = search_term.split('&') if '&' in search_term else search_term.split(' ')
    for s in search_terms:
        n_list = list()
        s = normalize('NFC', s)
        for r in results:
            t = normalize('NFC', r[0])
            # sys.stderr.write('Title: '+t+'\n')
            s = normalize('NFC', s)
            # sys.stderr.write("url: " + s + '\n')
            if s.lower() in t.lower():
                n_list.append(r)
    return n_list


Tools.log("PYTHON VERSION:", sys.version)
if sys.version_info < (3, 8):
    print('Python version 3.8.0 or higher required!')
    sys.exit(0)

wf = Items()
query = Tools.getArgv(1) if Tools.getArgv(1) is not None else str()
bms = paths_to_bookmarks()
fire_path = path_to_fire_bookmarks()

if fire_path:
    fire_bms = load_fire_bookmarks(fire_path)
    fire_bms = removeDuplicates(fire_bms)
    matches = match(query, fire_bms) if query != str() else fire_bms
    for ft, furl in matches:
        wf.setItem(
            title=ft,
            subtitle=furl,
            arg=furl,
            quicklook=furl
        )
        wf.addItem()

if len(bms) > 0:
    for bookmarks_file in bms:
        bm_json = get_json_from_file(bookmarks_file)
        bookmarks = get_all_urls(bm_json)
        matches = match(query, bookmarks)
        for m in matches:
            name = m[0]
            url = m[1]
            wf.setItem(
                title=name,
                subtitle=url,
                arg=url,
                quicklookurl=url
            )
            wf.addItem()

if wf.getItemsLengths() == 0:
    wf.setItem(
        title='No Bookmark found!',
        subtitle=f'Search "{query}" in Google...',
        arg=f'https://www.google.com/search?q={query}'
    )
    wf.addItem()
wf.write()
