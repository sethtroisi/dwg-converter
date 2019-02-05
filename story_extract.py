# -*- coding: utf8 -*-

import json
import os
import re
import sys
sys.setrecusionlimit = 10000

import multiprocessing as mp
from collections import Counter, defaultdict

import roman
from bs4 import BeautifulSoup
from tqdm import tqdm
from word2number import w2n

# shared code in utils.py
import utils


###### CONFIG VARIABLE ######


STORY_JSON_PATH="dwg_stories-2018_12_15.json"

MAX_HEADER = 500
MAX_FOOTER = 500

# This actually look very clean
SHOW_FILTERED_CHAPTERS = False
SHOW_BAD_CHAPTER_ORDER = False

# This are harder to tell but mostly look good.
PRINT_FOOTER_DIFFS = False

assert os.path.exists(utils.STORY_DIRECTORY)


def find_body(fn, soup):
    # <Html>
    # <head><title>A Blind Date</title><link rel=stylesheet type="text/css" href="/style/stories.css"></head>
    # <body bgcolor="#ffffff" vlink="#336666" background="back.gif">
    # <ul>
    # <center><h3><font size=+1 color="#336666">A Blind Date ~ Section V</font></h3></center>
    # <center><h3><font size=+1 color="#336666">By Meghan</font></h3></center>

    size_children = -1
    node = None
    for child in soup.recursiveChildGenerator():
        num_children = len(getattr(child, "contents", []))
        if num_children >= 10:
            test_size = len(str(child))
            if test_size > size_children:
                node = child
                size_children = test_size

    return node


def find_footer(fn, data):
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
        print_weird(fn)
        print(80 * "-")
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

# Take text and try to extract a chapter number from it.
def chapter_number(chapter):
    chapter = chapter.lower()
    chapter = re.sub(r'[:~,.()\n]', ' ', chapter)

    # Change some wierd wording titling choices
    chapter = re.sub('chapters', 'chapter', chapter)
    chapter = re.sub('chapter the', 'chapter', chapter)
    chapter = re.sub('^.*?chapter', '', chapter)

    # Drop most punctionation
    chapter = chapter.strip()

    if chapter == "":
        return None, chapter

    number = parse_number(chapter)
    return number, chapter


# Check if looks like a chapter on the HTML side.
def good_chapter(chapter):
    # Filter empty chapters
    if re.match('^\s*chapter\s*$', chapter, re.I):
        return False

    # If nothing else it's probably not a fake reference or in text
    if re.match('^\s*chapter [1-9][0-9]*\s*$', chapter, re.I):
        return True

    allowed_tags = ['h1', 'h2', 'b', 'font', 'title', 'big', 'center']
    if chapter.parent.name not in allowed_tags:
        # Check if we are <i> inside <center> or something

        node = chapter.parent
        while len(node.contents) <= 2:
            if node.name in allowed_tags:
                break
            node = node.parent
        else:
            return False

    if len(chapter) >= 100:
        return False

    return True


def filter_chapters(fn, chapters):
    # TODO filter centers not parts of a short text or
    # font, title, span, h1-4, b
    for chapter in chapters:
        # Check if HTML looks like a chapter (tags and stuff)
        if not good_chapter(chapter):
            if SHOW_FILTERED_CHAPTERS:
                print_weird('Filtered HTML Chapter {}: "{}"'.format(
                    fn, str(chapter.parent)[:100]).replace('\n', ''))
            continue

        text = chapter.string
        number, processed = chapter_number(text)
        if number is None:
            if SHOW_BAD_CHAPTER_ORDER:
                print_weird('Failed "{}" => "{}"'.format(text, processed))
            continue
        yield number


def extract(fn):
    return extract_story(fn, utils.get_file(fn))


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

    soup = BeautifulSoup(data, "lxml")

    # Append is now as simple as add new metadata at point
    # Add to jump list
    # Append body to other body.
    body = str(find_body(fn, soup))
    body_size = len(body)

    if body is None or body_size == 0:
        print("Didn't find body in", fn)
    elif len(data) > 3000 and body_size < 0.8 * len(data):
        print("Body({}) is {:.1f} for {}".format(
            body_size, 100.0 * body_size / len(data), fn))
        print ("\tend: \"{}\"".format(body[-50:].replace('\n', '')))

    footers = find_footer(fn, data)

    titles = soup.find_all('title')
    assert len(titles) <= 1, titles
    centers = soup.find_all('center')

    chapters = soup.find_all(string=re.compile('chapter', re.I))
    chapters = list(filter_chapters(fn, chapters))
    posted_ons = soup.find_all(string=re.compile('posted on', re.I))

    len_footers = [len(footer) for footer in footers]
    assert 10 < max(len_footers) < MAX_FOOTER, (len_footers, data[-MAX_FOOTER:])

    return (
        body,
        get_texts(titles),
        get_texts(centers),
        chapters,
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

        datas = pool.imap(extract, map(lambda e: e[1], sorted_processed))
        for i, ((url, fn), data) in enumerate(zip(tqdm(sorted_processed), datas)):

        #for i, (url, fn) in enumerate(tqdm(sorted_processed)):
        #    data = extract(fn)

            story_data[url] = data
            name = os.path.basename(url)

            #print (url, "\t", name)
            #print ("file://" + os.path.abspath(os.path.join(STORY_DIRECTORY, fn)))
            #print (",\n".join(map(str, data)))
            #print ("\n")
            if len(data) == 1:
                skipped += 1
                continue

            _, titles, centers, chapters, posted_ons, _ = data
            num_titles += len(titles) > 0
            num_centers += len(centers) > 0
            has_chapters += len(chapters) > 0
            has_posted_on += len(posted_ons) > 0
            if len(titles) > 0 and len(centers) > 0:
                #center_match_title += titles[0].lower() == centers[0].lower()
                center_match_title += centers[0].lower().startswith(titles[0].lower())

    print("{} files => {} stories".format(len(processed), len(groupings)))
    print()
    print("Title:", num_titles)
    print("Stories with <center>:", num_centers)
    print("Title == <center>:", center_match_title)
    print("Stories with chapters:", has_chapters)
    print("Stories with posted on:", has_posted_on)
    print("Skipped:", skipped)

    return story_data




########## MAIN ##############


with open(utils.URL_DATA_PATH, "r") as url_data_file:
    processed, out_links, groupings = json.load(url_data_file)
assert len(processed) > 0
assert len(out_links) > 0
assert len(groupings) > 0


# NOTE(SETH): set True and run once.
story_data = "story_datas.json"
#if True:
if False:
    datas = get_story_datas(processed)
    with open(story_data, 'w') as f:
        json.dump(datas, f)
else:
    with open(story_data, 'r') as f:
        datas = json.load(f)


html_pages = 0
stories = 0
multi_pagers = 0

multi_pages = 0
has_chapters = 0
has_incrementing_chapters = 0
count_chapters = 0

for story, urls in groupings.items():
    html_pages += len(urls)
    stories += 1

    if len(urls) == 1:
        continue

    multi_pagers += 1
    multi_pages += len(urls)

    if any(url not in processed for url in urls):
        print ("Skipping", story, "missing one or more parts")
        continue

    fns = [processed[url] for url in urls]
    story_datas = [datas[url] for url in urls]
    if any(len(data) == 1 for data in story_datas):
        continue

#    print(story)
#    print("\t", urls)
#    print("\t", fns)
    story_chapters = []
    all_chapters = []
    chapters_consistent = True
    for data in story_datas:
        assert len(data) == 6, urls

        _, titles, centers, chapters, posted_ons, _ = data

        has_chapters += len(chapters) > 0
        story_chapters.append(chapters)
        all_chapters.extend(chapters)

        if len(chapters) == 0:
            chapters_consistent = False

    chapters_are_sorted = len(all_chapters) and all_chapters == sorted(all_chapters)
    has_incrementing_chapters += chapters_consistent and chapters_are_sorted
    count_chapters += len(all_chapters)

    if not chapters_consistent and SHOW_BAD_CHAPTER_ORDER:
        print("\t", fns)
        print("\t", urls)
        print_weird(story_chapters)
        print()

one_pagers = stories - multi_pagers
print ("\n{} html pages => {} stories ({} ({:.1f}%) 1 page, {} ({:.1f}%) 2+ pages)".format(
    html_pages, stories,
    one_pagers, 100 * one_pagers / stories,
    multi_pagers, 100 * multi_pagers / stories))


print ("{} multi-page-stories made up of {} pages".format(multi_pagers, multi_pages))
print ("\t{} ({:.1f}%) stories have perfect chapter order".format(
    has_incrementing_chapters, 100 * has_incrementing_chapters / multi_pagers))
print ("\t{} ({:.1f}%) pages have chapters ({} total chapters)".format(
    has_chapters, 100 * has_chapters / multi_pages, count_chapters))

