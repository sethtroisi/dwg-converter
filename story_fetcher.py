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

INPUT_CSV_PATH = "dwg-posts-2018-12-11.csv"
STORY_JSON_PATH="dwg_stories-2018_12_15.json"
STORY_DIRECTORY = "stories/"


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


#Input CSV file should have the following columns with names specified in main below:
archive_url_indx = 8

if not os.path.exists(STORY_DIRECTORY):
    os.mkdir(STORY_DIRECTORY)

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()

def get_file(cached_filename, url):
    # this finds, caches, and opens a copy of a remote file

    # Check if we already downloaded & saved locally
    cache_name = STORY_DIRECTORY + cached_filename

    if os.path.exists(cache_name):
        with open(cache_name, "r", encoding="utf-8") as cached:
            page_data = cached.read()

    else:
        print('SKIPPING DOWNLOARD ATTEMPT FOR NOW')
        assert False, "SKIPPING RIGHT NOW AS REMAINING URLS ALL FAIL"

        print('Downloading "{}" => "{}"'.format(url, cached_filename))
        assert url.startswith("https:"), url

        request = urllib.request.urlopen(url)
        charset = request.info().get_content_charset("latin-1")
        page_data = request.read().decode(charset)
        page_data = page_data.replace(
           '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
           '')
        with open(cache_name, "w", encoding="utf-8") as cached:
           cached.write(page_data)
        time.sleep(2)

    return page_data

def get_csv_archive_urls():
    with open(INPUT_CSV_PATH, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        csv_input = list(csv_reader)

        print("Fetching Dwiggie posts from: ", INPUT_CSV_PATH);
        print("Number of rows: {}, number of columns: {}".format(
            len(csv_input), len(csv_input[0])))
        print()

        header = csv_input.pop(0)

        # verify important column assumptions
        assert header[archive_url_indx] == "archive real url"

        # While first entry of last line isn't a date
        while not ('200' in csv_input[-1][0] or '199' in csv_input[-1][0]):
            # remove the last line :)
            dropped = csv_input.pop()
            #print("Dropping:", ",".join(dropped))

        found = 0
        for i, line in enumerate(csv_input):
            # SETH NOTES yield is a fancy way of returning a list one item at a time
            #
            # def foo(x):
            #   for i in range(10):
            #       yield i
            #
            # def foo(x)
            #   values = []
            #   for i in range(10):
            #       values.append(i)
            #   return values
            archive_url = line[archive_url_indx]
            if archive_url != "":
                yield archive_url.replace('com//', 'com/')


def fetch_all_urls_recursively():
    archive_urls = list(get_csv_archive_urls())

    # Find any url that appears more than once
    url_counts = Counter(archive_urls)
    for k, v in url_counts.most_common():
        if v > 1:
            #print(k, "found", v, "times")
            archive_urls.remove(k)

    # Make sure none of them have the same name or things will get wierd
    urls = set(archive_urls)
    processed = {}
    filter_count = {name: 0 for name in FILTER_RE}
    weird = 0

    while len(urls) > 0:
        url = urls.pop()

        # Make sure we haven't already processed this url
        if url in processed: continue

        name = hash_url(url) + ".html"
        processed[url] = name # Store where it was saved locally.

        # These are just broken
        if "geocities" in url: continue

        # Name has overlaps so we use a hash of the string to save the file as
        if len(processed) % 100 == 0:
            print("{}/{}, {} => {}".format(
                len(processed), len(urls) + len(processed), url, name))

        try:
            page_data = get_file(name, url)
        except (urllib.error.HTTPError, AssertionError):
            print ('Got error with "{}" skipping'.format(url))
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
                    .replace('http://www.dwiggie.com/derby', '')
                    .replace('http://thedwg.com/derby', '')
                    .replace('/derby', '')
                )

                # We print this for now
                if any(sym in new_url for sym in ['://', '/', "#"]):
                    if not any(new_url.startswith(sym) for sym in ['old', 'ani/stories/']):
                        weird += 1

                        # NOTE(SETH): About 200 Urls most are to external sites
                        # Maybe 40 are for other dwiggie links ignoring those for now.
                        # print('Found wierd({}) looking url: "{}"'.format(weird, new_url))
                        continue

                if new_url == "":
                    continue

                # Handle these later
                if new_url in [
                    'http://austen.comoldc/lizm8.htm',
                ]:
                    continue


                # Figure out correct pointer
                if new_url.startswith('/'):
                    # Absolute path under dwiggie.com
                    new_url = "http://www.dwiggie.com/derby" + new_url
                    print ("Absolute Path:", new_url)
                else:
                    # Relative path in same directory
                    new_url = os.path.dirname(url) + "/" + new_url

                assert '//' not in new_url[7:], new_url
                matches.add(new_url)


        if len(matches) > 0:
            urls.update(matches)
#            print("\tFound {} links: {}".format(len(matches), sorted(matches)))

    print()
    print("Filtered Links:")
    for k, v in sorted(filter_count.items(), key=lambda l: -l[1]):
        print("\t{}: {}".format(k, v))
    print()
    print()

    print("Found {} files ({} not in CSV)".format(
        len(processed), len(processed) - len(archive_urls)))


    return processed

# MOVE SOMEWHERE WHICH HAS GROUPINGS
def dad_results(groupings, processed):
    def hash_name(name):
        return STORY_DIRECTORY + processed[name]

    def link_for_name(name):
        return '<a href="{}">{}</a>'.format(hash_name(name), name)

    scores = []
    for k, v in groupings.items():
        fn = v[0]

        if not re.search(r'[0-9a]\.htm$', fn) and not re.search(r'/[a-z]*\.htm$', fn):
            continue

        with open(hash_name(fn)) as f:
            page_data = f.read().lower()

        length = len(page_data)

        darcies = page_data.count(' darcy')
        liz = page_data.count('liz')

        words = max(length / 10, page_data.count(' '))
        words = min(length / 4, words)

        d_score = math.sqrt(1000 * darcies / words)
        l_score = math.sqrt(1000 * liz / words)
        w_score = (words / 1000) ** 0.6

        scores.append((
            d_score + l_score + w_score,
            d_score, l_score, w_score,
            v))

    scores.sort(reverse = True)

    with open("dad_results.html", "w") as results:
        results.write('''
    <html>
    <body>
    <h1>Dad Meta JAFF Search</h1>
    <p>Searched {} stories to bring you these scores
    <hr>
    <table>
        <tr>
            <th>Overal "Score"</th>
            <th>Darcy's/1000 words</th>
            <th>Liz's/1000 words</th>
            <th>Length</th>
            <th>link(s)</th>
        </tr>
    '''.format(len(scores)))

        for s, d,l,w, fns in scores[:50]:

            columns = [
                "{:.2f}".format(s),
                int(d**2),
                int(l**2),
                int(w**(1 / 0.6) * 1000),
                ",".join(link_for_name(fn) for fn in fns),
            ]

            row = "<tr>{}</tr>"
            values = "  <td>{}</td>"
            results.write(row.format("\n".join([values.format(v) for v in columns])))

        results.write('''
    </table>
    </body>
    </html>''')




########## MAIN ##############


processed = fetch_all_urls_recursively()

# Find any file in the CACHE_DIR that shouldn't be there
bad = []
for filename in os.listdir(STORY_DIRECTORY):
    # See if any current post points to this file.
    if filename not in processed.values():
        bad.append(filename)
#        os.remove(STORY_DIRECTORY + "/" + filename)
print("\n{} bad files: {}\n".format(len(bad), bad[:10]))

not_dl = []
for key, filename in processed.items():
    if not os.path.exists(STORY_DIRECTORY + filename):
        not_dl.append((key, filename))
for key, fn in not_dl:
    processed.pop(key)
print("\n{} not downloaded files:".format(len(not_dl)))
for n in not_dl[:10]:
    print("\t", n)
print()


print("\n{} files".format(len(processed)))

with open(STORY_JSON_PATH, "w") as story_json_file:
    json.dump(processed, story_json_file)
