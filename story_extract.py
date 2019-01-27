# -*- coding: utf8 -*-

import json
import os
import re

import multiprocessing as mp
from collections import Counter, defaultdict

import roman
from bs4 import BeautifulSoup
from tqdm import tqdm
from word2number import w2n

STORY_JSON_PATH="dwg_stories-2018_12_15.json"
STORY_DIRECTORY = "stories/"

DWIGGIE_PREFIX = "https://www.dwiggie.com/derby/"

MAX_HEADER = 500
MAX_FOOTER = 500
PRINT_COUNT = 0

# This actually look very clean
SHOW_FILTERED_CHAPTERS = False
SHOW_BAD_CHAPTER_ORDER = False

# Show any oddities with names of stories
SHOW_STORY_NAMING_ODDITIES = False

# This are harder to tell but mostly look good.
PRINT_FOOTER_DIFFS = False



def print_weird(*objects, **kwargs):
    global PRINT_COUNT
    PRINT_COUNT += 1
    print("(", PRINT_COUNT, ") ", sep="", end="")
    print(*objects, **kwargs)
    print()


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


def find_body(fn, soup):
    # <Html>
    # <head><title>A Blind Date</title><link rel=stylesheet type="text/css" href="/style/stories.css"></head>
    # <body bgcolor="#ffffff" vlink="#336666" background="back.gif">
    # <ul>
    # <center><h3><font size=+1 color="#336666">A Blind Date ~ Section V</font></h3></center>
    # <center><h3><font size=+1 color="#336666">By Meghan</font></h3></center>

    for child in soup.recursiveChildGenerator():
        if len(getattr(child, "contents", [])) > 10:
            return len(child.contents), len(str(child))


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

    soup = BeautifulSoup(data, "lxml")

    # Append is now as simple as add new metadata at point
    # Add to jump list
    # Append body to other body.
    body = find_body(fn, soup)

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

        #for i, (url, fn) in enumerate(sorted_processed):
        #    data = extract(fn)

        datas = pool.imap(extract, map(lambda e: e[1], sorted_processed))
        for i, ((url, fn), data) in enumerate(zip(tqdm(sorted_processed), datas)):
#            if i > 100:
#                break

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


with open(STORY_JSON_PATH, "r") as story_json_file:
    processed, out_links = json.load(story_json_file)
assert len(processed) > 0
assert len(out_links) > 0


# Recursively build the list of urls reachable by clicking links
# NOTE: because of "beginning" links the group is the same no matter
# what story you start with in the group.

groupings = {}
seen = set()
for url in processed:
    if url in seen:
        # part of some existing group
        continue

    open_links = set(out_links[url])
    group = set([url])

    while len(open_links):
        other = open_links.pop()

        if other in group: continue
        group.add(other)

        if other in out_links:
            open_links.update(out_links[other])
        else:
            print("Not processed?:", other)

    # need some "canonical" url
    leader = min(group)

    # sort 1aa after 1z
    group = sorted(group, key=lambda e: (len(e), e))

    groupings[leader] = group
    seen.update(group)

    if len(group) > 1 and SHOW_STORY_NAMING_ODDITIES:
        prefix = os.path.commonprefix(group)
        suffix = [g[len(prefix):].replace('.htm', '') for g in group]

        # Known wierd case of <author> folled by <author>1b
        test = [""] + ['1' + chr(98 + i) for i in range(len(group) - 1)]
        known_issue = test == suffix

        if not known_issue and (suffix[0] != "" or any(len(u) > 1 for u in suffix)):
            print_weird(prefix + suffix[0] + ".htm", suffix)


def print_grouping_info(groups):
    page_count = Counter([len(group) for group in groups.values()])
    print ("{} groupings:".format(sum(page_count.values())))
    for pages, count in sorted(page_count.items()):
        print ("\t{} pages x {} stories".format(pages, count))


print_grouping_info(groupings)
print()


'''
groupings_b = {}
for name in processed:
    #name = name.replace('https://www.dwiggie.com/', '')

    # path (e.g /old_2007/) matters
    path = os.path.dirname(name)
    title = os.path.basename(name)

    match = re.match('([a-z]+[0-9]*)([a-z]*).htm', title)
    if not match:
        # About 20 files like ann1_2.htm, laura8-9.htm
        print_weird(name)
        continue

    assert title.endswith('.htm'), (name, processed[name])
    title, part = match.groups()
    if len(part) > 1:
        print_weird(title)
        continue

    key = path + '/' + title + '.htm'
    if key not in groupings_b:
        groupings_b[key] = []
    groupings_b[key].append(name)

for k in groupings_b:
    groupings_b[k].sort()

print_grouping_info(groupings_b)
print()

def shorten(l):
    return [a.replace(DWIGGIE_PREFIX, "DWG/") for a in l]

for k in sorted(set(groupings.keys()) | set(groupings_b.keys())):
    a = groupings.get(k, [])
    b = groupings_b.get(k, [])
    if a != b:
        print_weird("Mismatch ({:30}):".format(k), shorten(a), shorten(b))
'''

# NOTE(SETH): set True and run once.
story_data = "story_datas.json"
if True:
#if True:
    datas = get_story_datas(processed)
    with open(story_data, 'w') as f:
        json.dump(datas, f)
else:
    with open(story_data, 'r') as f:
        datas = json.load(f)


multi_page = 0
pages = 0
has_chapters = 0
has_incrementing_chapters = 0
count_chapters = 0
for story, urls in groupings.items():
    if len(urls) == 1:
        continue

    multi_page += 1

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
        if len(data) == 1:
            break

        pages += 1

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

print ("{} multi-page-stories, {} pages, {} with chapters, {} with good chapter order, {} total chapters"
    .format(multi_page, pages, has_chapters, has_incrementing_chapters, count_chapters))
