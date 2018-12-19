# -*- coding: utf8 -*-

import json
import os
import re

import multiprocessing as mp
from collections import Counter

import roman
from bs4 import BeautifulSoup
from tqdm import tqdm
from word2number import w2n


STORY_JSON_PATH="dwg_stories-2018_12_15.json"
STORY_DIRECTORY = "stories/"

MAX_FOOTER = 500
PRINT_FOOTER_DIFFS = False

assert os.path.exists(STORY_DIRECTORY)

def get_file(cached_filename):
    # this finds, caches, and opens a copy of a remote file

    # Check if we already downloaded & saved locally
    cache_name = STORY_DIRECTORY + cached_filename

    if os.path.exists(cache_name):
        with open(cache_name, "r", encoding="utf-8") as cached:
            page_data = cached.read()
        return page_data

    print('FILES SHOULD ALREADY BE DOWNLOADED')
    assert False

disagree = 0
def find_footer(fn, data):
    global disagree

    # Good optimization
    data = data[-MAX_FOOTER:]

    # Footer method 1
    # I've seen '<hr>', '<hr >', '<hr />'
    end1 = data.rfind('<hr')
    if end1 >= 0:
        end1 = data.rfind('\n', 0, end1)

        footer1 = data[end1:]
        footer1 = footer1.strip()
    else:
        footer1 = ""

    # Footer method 2
    end2 = data.rindex('Copyright') + 9
    while True:
        end2_last = end2
        end2 = data.rfind('\n', 0, end2)
        line = data[end2:end2_last].strip()

        if end2 == -1 or len(line) > 100:
            end2 = end2_last
            break
        if line in ['', '<p>']:
            continue
        if any(w in line for w in ['Copyright', 'a href', '<hr']):
            continue
        end2 = end2_last
        break
    footer2 = data[end2:]
    footer2 = footer2.strip()

    if PRINT_FOOTER_DIFFS and footer1 != footer2:
        disagree += 1
        print()
        print(fn)
        print(disagree, 40 * "-")
        if footer1 == "":
            print("No footer1:")
            print(footer2)
        elif footer2 == "":
            print("No footer2:")
            print(footer1)
        else:
            assert len(footer2) > len(footer1), (len(footer1), len(footer2), data)
            print(footer2[:-len(footer1)])
            print("BOTH:")
            print(footer1)

    return footer1, footer2


def extract(fn):
    return extract_story(fn, get_file(fn))

def extract_story(fn, data):
    # grab story and author from center tags.
    # find <hr> ... Beginning, <links> ... <hr>
    #    <STORY>
    #   [link to next]
    # <hr>
    # copyright

    if 'xmlns:w="urn:schemas-microsoft-com:office:word"' in data[:1000]:
        return ['Wierd Word Document']

    if 'Copyright held by' not in data[-MAX_FOOTER:]:
        return ['No Copyright']

    def get_texts(nodes):
        return [node.get_text().strip() for node in nodes]

    # get NavigableString texts
    def get_ns_texts(nodes):
        return [node.string.strip() for node in nodes]

    try:
        footers = find_footer(fn, data)
    except:
        print()
        print(fn)
        raise

    soup = BeautifulSoup(data, "lxml")

    titles = soup.find_all('title')
    assert len(titles) <= 1, titles
    centers = soup.find_all('center')

    hrs = soup.find_all('hr')

    chapters = soup.find_all(string=re.compile('chapter', re.I))
    posted_ons = soup.find_all(string=re.compile('posted on', re.I))

    len_footers = [len(footer) for footer in footers]
    assert 10 < max(len_footers) < MAX_FOOTER, (len_footers, data[-MAX_FOOTER:])


    return (
#        data,
        "",
        get_texts(titles),
        get_texts(centers),
        get_ns_texts(chapters),
        get_ns_texts(posted_ons),
        len_footers,
    )


def get_story_datas(needed):
    story_data = {}
    num_titles = 0
    num_centers = 0
    has_chapters = 0
    has_posted_on = 0
    center_match_title = 0
    skipped = 0

    with mp.Pool(3) as pool:
        sorted_processed = sorted(needed.items())

        #for i, (url, fn) in sorted_processed:
        #    data = extract(fn, get_file(fn))

        datas = pool.imap(extract, map(lambda e: e[1], sorted_processed))

        for i, ((url, fn), data) in enumerate(zip(tqdm(sorted_processed), datas)):
        #    if i > 100:
        #        break

            story_data[url] = data
            name = os.path.basename(url)

        #    print (url, "\t", name)
        #    print ("file://" + os.path.abspath(os.path.join(STORY_DIRECTORY, fn)))
        #    print (",\n".join(map(str, data)))
        #    print ("\n")
            if len(data) == 1:
                skipped += 1
                continue

            _, titles, centers, chapters, posted_ons, _ = data
            num_titles += len(titles) > 0
            num_centers += len(centers) > 0
            has_chapters += len(chapters) > 0
            has_posted_on += len(posted_ons) > 0
            if len(titles) > 0 and len(centers) > 0:
                center_match_title += titles[0].lower() == centers[0].lower()
                #center_match_title += centers[0].lower().startswith(titles[0].lower())

    print("{} files => {} stories".format(len(processed), len(groupings)))
    print()
    print("Title:", num_titles)
    print("Stories with <center>:", num_centers)
    print("Title == <center>:", center_match_title)
    print("Stories with chapters:", has_chapters)
    print("Stories with posted on:", has_posted_on)
    print("Skipped:", skipped)

    return story_data

def parse_number(number):
    roman_text = re.match(r'^([ivxlc]+)\b', number)
    if roman_text:
        return roman.fromRoman(roman_text.group(1).upper())

    # '5 - asdf', '12(ii)', '70b'
    num = re.match(r'^([1-9][0-9]*)[abcd]?\b', number)
    if num:
        return int(num.group(1))

    try:
        return w2n.word_to_num(number)
    except:
        return None

def parse_chapters(chapters):
    parsed = []
    for chapter in chapters:
        og_chapter = chapter
        chapter = chapter.lower()
        chapter = chapter.replace('\n', '')
        chapter = re.sub('^.*?chapter', '', chapter)

        # Drop most punctionation
        chapter = re.sub(r'[:~,.()]', ' ', chapter)
        chapter = chapter.strip()

        if chapter == "":
            continue

        number = parse_number(chapter)
        if number is None:
            # NOTE(seth): remaining bad chapters appear to mostly be from use of chapter in the text.
            # print('Failed "{}" => "{}"'.format(og_chapter, chapter))
            continue

        parsed.append(number)

    return parsed




########## MAIN ##############


with open(STORY_JSON_PATH, "r") as story_json_file:
    data = json.load(story_json_file)

processed = data.pop('names')
groupings = data.pop('stories')
assert len(data) == 0

needed = {}
for story, urls in groupings.items():
    if len(urls) > 1:
        for url in urls:
            needed[url] = processed[url]

# NOTE(SETH): toggle False to True and run once.
story_data = "story_datas.json"
if False:
    datas = get_story_datas(needed)
    with open(story_data, 'w') as f:
        json.dump(datas, f)
else:
    with open(story_data, 'r') as f:
        datas = json.load(f)

multi_part = 0
has_chapters = 0
has_incrementing_chapters = 0
bad_chapters = 0
for story, urls in groupings.items():
    if len(urls) == 1:
        continue

    multi_part += 1

    # FOUND A PROBLEM
    # NOTE(SETH): rebekah1b.htm and rebekah1c.htm but part a is rebekah.htm

    fns = [processed[url] for url in urls]
    story_datas = [datas[url] for url in urls]
    if any(len(data) == 1 for data in story_datas):
        continue

#    print(story)
#    print("\t", urls)
#    print("\t", fns)
    had_bad_chapters = 0
    all_chapters = []
    for data in story_datas:
        if len(data) == 1:
            break

#        print("\t", data)

        _, titles, centers, chapters, posted_ons, _ = data
        parsed_chaps = parse_chapters(chapters)
#        print (parsed_chaps)
        all_chapters.extend(parsed_chaps)

        if len(parsed_chaps) != len(chapters):
            had_bad_chapters += 1

    has_chapters += len(all_chapters) > 0
    has_incrementing_chapters += had_bad_chapters == 0 and \
        all_chapters == sorted(all_chapters)
    bad_chapters += had_bad_chapters > 0

    print()


print ("{} multi-part-stories, {} with chapters, {} with good chapter order, {} with bad chapters"
    .format(multi_part, has_chapters, has_incrementing_chapters, bad_chapters))
