# -*- coding: utf8 -*-

import csv
import json
import re
import os
from collections import Counter
import urllib

# shared code in utils.py
import utils


###### CONFIG VARIABLE ######


SHOW_EXTERNAL_LINKS = False

INPUT_CSV_PATH = 'dwg-posts-2019-01-26.csv'
STORY_JSON_PATH= 'dwg_stories-2018_12_15.json'


LINK_RE = re.compile(r'<a href="([^"]*)"')

# Link to another post in this series probably.
OTHER_PAGE_RE = re.compile(r'[a-z]*[0-9]*[a-z]*.htm#new[0-9]*')

# Don't forget commas at the end of the line!
FILTER_RE = [
    '^#(new|note|song|)',
    OTHER_PAGE_RE,
    'index.(htm|php)$',
    '^mailto:',
    '\.(jpg|wav)$',

    # Part of a template at some point.
    '\*{4,10}.htm',

    'austen.com',
    'youtube.com',
    'tumblr.com',
    'pemberley.com',
    'wikipedia.org',
]

DERBY_DIRS = [
    '/derby/',
    '/ani/',
]


#Input CSV file should have the following columns with names specified in main below:
archive_url_indx = 8

if not os.path.exists(utils.STORY_RAW):
    os.mkdir(utils.STORY_RAW)

if not os.path.exists(utils.STORY_DIRECTORY):
    os.mkdir(utils.STORY_DIRECTORY)

def get_csv_archive_urls():
    with open(INPUT_CSV_PATH, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        csv_input = list(csv_reader)

        print('Fetching Dwiggie posts from: ', INPUT_CSV_PATH);
        print('Number of rows: {}, number of columns: {}'.format(
            len(csv_input), len(csv_input[0])))
        print()

        header = csv_input.pop(0)

        # verify important column assumptions
        assert header[archive_url_indx] == 'archive real url'

        # While first entry of last line isn't a date
        while not re.match(r'^(20[01][0-9]|19[89][0-9])',  csv_input[-1][0]):
            # remove the last line :)
            dropped = csv_input.pop()
        #    print('Dropping:', ','.join(dropped))
        #print('Not Dropping:', ','.join(csv_input[-1]))

        found = 0
        for i, line in enumerate(csv_input):
            archive_url = line[archive_url_indx]
            if archive_url != '':
                yield archive_url


def fetch_all_urls_recursively():
    archive_urls = list(get_csv_archive_urls())

    # Find any url that appears more than once
    url_counts = Counter(archive_urls)
    for k, v in url_counts.most_common():
        if v > 1:
            #print(k, 'found', v, 'times')
            archive_urls.remove(k)

    # url => local file name
    processed = {}
    # url => list of other urls on that page
    out_links = {}

    # current urls to explore
    urls = set(archive_urls)
    filter_count = {name: 0 for name in FILTER_RE}
    weird = 0

    while len(urls) > 0:
        url = urls.pop()

        # Make sure we haven't already processed this url
        if url in processed: continue

        # Two broken items in CSV
        if 'geocities' in url:
            continue

        # Name has overlaps if different directories
        # so we use a hash of the string to save the file
        name = utils.hash_url(url) + '.html'

        # Store where it was saved locally.
        processed[url] = name
        out_links[url] = []

        if len(processed) % 500 == 0:
            print('{}/{}, {} => {}'.format(
                len(processed), len(urls) + len(processed), url, name))

        try:
            # Use this if you don't want to retry downloads
            skip_download = False
            page_data = utils.get_file(name, None if skip_download else url)
        except Exception as e:
            print('Got error with "{}" skipping: {}'.format(url, e))
            print()
            continue

        raw_matches = re.findall(LINK_RE, page_data)

        matches = set()
        for new_url in raw_matches:
            new_url = new_url.strip()

            for filter_re in filter_count:
                if re.search(filter_re, new_url):
                    filter_count[filter_re] += 1
                    break
            else:
                # This clause happens if new_url wasn't filtered
                new_url = (new_url
                    .replace('http://www.dwiggie.com', '')
                    .replace('http://thedwg.com', '')
                )
                if new_url == '':
                    continue

                # We print this for now
                if any(sym in new_url for sym in ['://', '/', '#']):
                    if not any(new_url.startswith(sym) for sym in DERBY_DIRS):
                        weird += 1

                        # NOTE(SETH): About 200 Urls most are to external sites
                        # Maybe 40 are for other dwiggie links ignoring those for now.
                        if SHOW_EXTERNAL_LINKS:
                            print('Found wierd({}) looking url: "{}"'.format(
                                weird, new_url))
                        continue

                # Figure out correct pointer
                if new_url.startswith('/'):
                    # Absolute path under dwiggie.com
                    new_url = 'https://www.dwiggie.com' + new_url
                    #print ('Absolute Path:', new_url)
                else:
                    # Relative path in same directory
                    new_url = os.path.dirname(url) + '/' + new_url

                assert '//' not in new_url[7:], new_url
                matches.add(new_url)

        if len(matches) > 0:
            urls.update(matches)
            out_links[url] = sorted(matches)
            #print('\tFound {} links: {}'.format(len(matches), sorted(matches)))

    print('\nFiltered Links:')
    for k, v in sorted(filter_count.items(), key=lambda l: -l[1]):
        print('\t{}: {}'.format(k, v))

    print('\n\nFound {} files ({} not in CSV)'.format(
        len(processed), len(processed) - len(archive_urls)))
    return processed, out_links


########## MAIN ##############


processed, out_links = fetch_all_urls_recursively()

# Find any file in the CACHE_DIR that shouldn't be there
bad = []
for filename in os.listdir(utils.STORY_DIRECTORY):
    # See if any current post points to this file.
    if filename not in processed.values():
        bad.append(filename)
#        os.remove(utils.STORY_DIRECTORY + '/' + filename)
if len(bad):
    print('\n{} bad files: {}\n'.format(len(bad), bad[:10]))


not_dl = []
for key, filename in processed.items():
    if not os.path.exists(utils.STORY_DIRECTORY + filename):
        not_dl.append((key, filename))
for key, fn in not_dl:
    processed.pop(key)
    out_links.pop(key)
print('\n{} not downloaded files:'.format(len(not_dl)))
for key in not_dl:
    print('\t', key)


print('\n\n{} files'.format(len(processed)))
print('\twith {} outgoing links'.format(
    sum([len(links) for links in out_links.values()])))

# Save this data to a file for use in story_extract.py
with open(STORY_JSON_PATH, 'w') as story_json_file:
    json.dump((processed, out_links), story_json_file)
