# -*- coding: utf8 -*-

import csv
import hashlib
import json
import os
import math
import re
import time
import urllib.request

from collections import Counter

STORY_JSON_PATH="dwg_stories-2018_12_15.json"
STORY_DIRECTORY = "stories/"

assert os.path.exists(STORY_DIRECTORY):

def get_file(cached_filename, url):
    # this finds, caches, and opens a copy of a remote file

    # Check if we already downloaded & saved locally
    cache_name = STORY_DIRECTORY + cached_filename

    if os.path.exists(cache_name):
        with open(cache_name, "r", encoding="utf-8") as cached:
            page_data = cached.read()
        return page_data

    print('FILES SHOULD ALREADY BE DOWNLOADED')
    assert False


########## MAIN ##############


with open(STORY_JSON_PATH, "r") as story_json_file:
    data = json.load(story_json_file)

    processed = data.pop('names')
    groupings = data.pop('stories')
    assert len(data) == 0


