# Brenda Troisi 11/19/2020
# This program fetches the components of a story from fanfiction.com and assembles them
# into a single, passable html file. 
# Unfortunately, it no longer works reliably for me. You need to scan the resulting doc looking for "ROBOT". Everywhere that appears, the content of a page was denied...


# -*- coding: utf8 -*-
import os.path
import urllib.request
# import datetime
# import re
import sys
import time
import cloudscraper
# from collections import Counter

#-----------------------

ONLY_A_FEW = False
# TODO need to toggle off for final run.
MOVING_FAST_BREAKING_THINGS = False  # amongst other things, this enables file caching
LOOP_DELAY = 120  #in seconds

#-----------------------

CACHE_DIRECTORY = "cache/"

HTML_HDR = "<Html>      \
<head>  \
<meta charset=\"utf-8\"> \
<ul>"
HTML_FTR = "</ul>    \
</body>     \
</html>"
HTML_TITLE_PREAMBLE = "<div align=center class='lc-wrapper' style='margin-top:10px;'><strong>"
HTML_TITLE_POST = "</strong>"

BR_TAG = "<br/>"
HR_TAG = "<hr>"
ITALIC_TAG = "<i>"
ITALIC_END_TAG = "</i>"
BOLD_TAG = "<b>"
BOLD_END_TAG = "</b>"

EMPTY_LINE = "<p>"
SEPARATOR_LINE = "<p><hr><p>"  # this draws visual horizontal lines.

EMPTY_LINE_FF = "</em></p><p>"  # Fanfiction has different conventions?
BR_TAG_FF = "<br></em><em>"

# -----------------------

IS_LINUX = sys.platform.lower().startswith('linux')


def cached_path(filename):
    return os.path.join(CACHE_DIRECTORY, filename)


def get_file(cached_filename, url=''):
    # this finds, caches, and opens a copy of a file.
    # for running the program, we don't need the indiv files.
    # but for debugging, it's good to cache them locally

    # Check if we already downloaded & saved locally
    cached_name = cached_path(cached_filename)

    if MOVING_FAST_BREAKING_THINGS and os.path.exists(cached_name):
        with open(cached_name, "r", encoding="utf-8") as cached:
            page_data = cached.read()

    else:
        assert url.startswith("https:"), url

        # original: page_data = urllib.request.urlopen(url).read().decode("utf-8")
        # changed to: request = urllib.request.urlopen(url) plus 
        #    this was getting 403 error, so trying to add user-agent:
        #req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        #request = urllib.request.urlopen(req)
        #charset = request.info().get_content_charset("latin-1")
        #page_data = request.read().decode(charset)
        #page_data = scraper.get(url).text  <- this stopped working
        # but this didn't work either so, as per seth, I'm trying cloudscraper:
        scraper = cloudscraper.create_scraper() 
        page_data = scraper.get(url).content
        # but that stopped working: cloudflare version 2 captcha challenge, unsupported"

        page_data = html_cleanup(page_data)
        if MOVING_FAST_BREAKING_THINGS:  # cache the file locally
            with open(cached_name, "w", encoding="utf-8") as cached:
                cached.write(page_data)
            print("\tDownloaded: " + url)
   
    time.sleep(LOOP_DELAY)		#try to look less like a robot!
    return page_data


url_prefix = "https://www.fanfiction.net/s/"


def flatten_filename(filename):
    # we're fetching files from a file structure that we don't want to duplicate for local copies
    return filename.replace(url_prefix, "").replace("/", "_")


def fetch_page_data(url):  # e.g. https://www.fanfiction.net/s/12604647/1/All-Dogs-Go-To-Heaven
    # print ("fetching file: " + url)
    # TODO do we need to save it as a file? Best to cache while debugging, change later?
    local_filename = flatten_filename(url)
    page_data = get_file(local_filename, url)
    return page_data

#TODO: these markers have changed over time, wo reverify
title_preamble = "Follow/Fav</button><b class='xcontrast_txt'>"   
title_post = BOLD_END_TAG
header_preamble = "<span class='xcontrast_txt'><div style='height:5px'></div>By:</span> <a class='xcontrast_txt'"
header_post = "<div align=center class='lc-wrapper' style='margin-top:10px;'><div class='lc'>"
chapters_preamble = "Chapters: "
chapters_post = " "
chapter_text_preamble = "<div class='storytext xcontrast_txt nocopy' id='storytext'>"
chapter_text_post = "</div>"


def extract_header(page_data):  # TODO this ought to parse the html? But I'm going for crude:
    title_start = page_data.find(title_preamble) + len(title_preamble)
    title_end = page_data.find(title_post, title_start)
    header_start = page_data.find(header_preamble)
    header_end = page_data.find(header_post, header_start)
    chapters_start = page_data.find(chapters_preamble, header_start) + len(chapters_preamble)
    chapters_end = page_data.find(chapters_post, chapters_start)

    # TODO  more precise extraction of header fields...
    # TODO the hyperlink for the author did not translate?
    # save the title/url, author/url, blurb, published and updated dates, completion status:
    header_data = HTML_TITLE_PREAMBLE \
                  + page_data[title_start:title_end] + SEPARATOR_LINE \
                  + HTML_TITLE_POST \
                  + page_data[header_start:header_end] + SEPARATOR_LINE

    num_chapters = int(page_data[chapters_start:chapters_end])
    return num_chapters, header_data


def extract_chapter_text(page_data):  # TODO ditto on the crude...
    chapter_text_start = page_data.find(chapter_text_preamble) + len(chapter_text_preamble)
    chapter_text_end = page_data.find(chapter_text_post, chapter_text_start)
    chapter_data = page_data[chapter_text_start:chapter_text_end] + SEPARATOR_LINE
    return chapter_data


def write_story_to_file(story_filename, story_data):
    # TODO this is still  html, it needs to be converted to text
    # For now, will make it acceptable html

    # Aid in the readability of html files:
    chars_per_line = len(story_data) / (story_data.count("\n") + 1)
    if chars_per_line > 500:
        # Add artificial newline to the post in the html file
        story_data = story_data.replace(BR_TAG_FF, BR_TAG_FF + "\n")

    with open(story_filename, "w", encoding="utf-8") as cached:
        cached.write(HTML_HDR + story_data + HTML_FTR)


########## MAIN ##############
print("This will fetch and consolidate all the pages of a story as formatted on fanfiction.com")
print("Unfortunately, it no longer works reliably. You need to scan the resulting doc looking for ROBOT. Everywhere that appears, the content of a page was denied...\n")


# Outer loop runs once per story:
while True:
    # Request the story url - assumed to be on fanfiction.com
    url = input("url of story to fetch from fanfiction.com: ")
    # e.g. https://www.fanfiction.net/s/12604647/1/All-Dogs-Go-To-Heaven
    if not url:
        break
    # TODO: should I do some verification on url or just try it and allow to fail?

    URL_COMMENT_PRE = '\n<!--  '
    URL_COMMENT_POST = '  -->\n'

    # this will accumulate the text to be written to file:
    story_data = URL_COMMENT_PRE + url + URL_COMMENT_POST + SEPARATOR_LINE

    # Fetch the first page data from the url:
    page_data = fetch_page_data(url)

    # extract the header info from the html:
    number_of_chapters, header_data = extract_header(page_data)
    story_data = story_data + header_data

    #   Inner loop which fetches each chapter of the story:
    for current_chapter in range(1, number_of_chapters+1):
        print("fetching chapter " + str(current_chapter))
        if current_chapter != 1:
            old_str = "/" + str(current_chapter - 1) + "/"
            new_str = "/" + str(current_chapter) + "/"
            url = url.replace(old_str, new_str)
            page_data = fetch_page_data(url)

        # for all cases, extract chapter text and append it to the story
        story_data = story_data + extract_chapter_text(page_data)  # TODO how to do the append?

        current_chapter += 1
        if ONLY_A_FEW and current_chapter >= 4:
            break

    # TODO write story_data to a local file - need the filename?
    story_filename = input("filename for completed story: ")
    # with open(story_filename+".html", "w", encoding="utf-8") as cached:
    #       cached.write(story_data)
    write_story_to_file(story_filename, story_data)
