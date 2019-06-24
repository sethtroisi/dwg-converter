# -*- coding: utf8 -*-
import csv
import os.path
import urllib.request
import datetime
import re
import sys
import subprocess
import time
import tempfile
from collections import Counter
from bs4 import BeautifulSoup

from story_fixer import fix_one_file

#-----------------------

DOWNLOAD_FIRST = False
ONLY_A_FEW = False
# TODO need to toggle off for final run.
MOVING_FAST_BREAKING_THINGS = False

#------------------------

INPUT_CSV_PATH = "dwg - posts.csv"
OUTPUT_CSV_PATH="dwg_archive_results.csv"

#Input CSV file should have the following columns with names specified in main below:
post_date_index = 0
creation_date_index = 1
msg_id_index = 2
author_id_index = 3
author_index = 4
title_index = 5
action_index = 6
category_index = 7
post_url_index = 8
archive_url_index = 9
final_post_index=10
which_book_index=11
blurb_index=12
short_url_index=15
last_csv_input_index=15
#The output CSV file will have the same columns as input (previous list) plus this immediately after:
to_archive_filename_index=16

#-----------------------

ARCHIVE_TEMPLATE = "templates/story_archive_template.html"
CACHE_DIRECTORY = "cache/"

#-----------------------

# For JUMP_SECTION
JUMP_LINK_INSERTION_MARKER = '<span id="new-jumps-go-here"></span>'
JUMP_SECTION = '<span class="navigation-links">'
JUMP_TEMPLATE = f'''
{JUMP_SECTION}
    {{jump_link}}
    {JUMP_LINK_INSERTION_MARKER}
</span>'''

# For POST_BODY_SECTION
STORY_TEMPLATE = '''
<div class="post">
  <hr><br/><br/>
  {jump_label}<i>Posted on {date}</i><br/><br/>
  {body}
</div>
'''

# For CLOSING_SECTION
STORY_STATUS_MARKER = '<span id="story-insertion-marker closing-status"><p>'
STORY_STATUS_MARKER_CLOSE = '</p></span>'
CLOSING_STATEMENT='<font color="#336666" size="+1">{}</font>'
CLOSING_TBC = CLOSING_STATEMENT.format("To Be Continued ...")
CLOSING_THE_END = CLOSING_STATEMENT.format("The End")
# We don't need a 2nd marker but a better description is nice
STORY_INSERTION_MARKER = STORY_STATUS_MARKER

# From STORY_STATUS_MARKER to end of file (closing section + ToBeContinued + copyright + boilerplate html)
FINAL_SECTION_LENGTH_MAX = 220 # ToBeContinued is like really long man.

#-----------------------

BR_TAG = "<br/>"
HR_TAG = "<hr>"
ITALIC_TAG = "<i>"
ITALIC_END_TAG = "</i>"
BOLD_TAG = "<b>"
BOLD_END_TAG = "</b>"

SEPERATOR_LINE = "<p><hr><p>"        # this draws visual horizontal lines.

#-----------------------

IS_LINUX = sys.platform.lower().startswith('linux')


def str_equal(a, b):
    a = a.strip().casefold()
    b = b.strip().casefold()
    return a == b


def loose_equal(a, b):
    #Make sure that a and b are roughly error
    a = a.strip().casefold()
    b = b.strip().casefold()
    if a == b:
        return True
    if len(a) > 5 and b.startswith(a):
        return True
    if len(b) > 5 and a.startswith(b):
        return True
    return False


def create_filename(author, title, post_date):
    #use first 15 printable chars of author concatenated with first 15 of title + posting date
    #filename = add 10 of author
    author = re.sub('[^A-Za-z0-9]', '', author)
    title = re.sub('[^A-Za-z0-9]', '', title)
    post_date = re.sub('[^A-Za-z0-9]', '', post_date)
    filename = cached_path(author[:10] + title[:15] + post_date + ".html")
    return filename


def strip_post_space(data):
    data = data.strip()

    hr_br_or_space = r'(\s*<[bh]r */?>\s*)*'
    data = re.sub(r'^' + hr_br_or_space, '', data)
    data = re.sub(hr_br_or_space + r'$', '', data)
    return data


def strip_comment(post, post_name):
    # Run this after Using story_fixer.py which will embed each DNA section in a DNA tag
    # This strips the text of each of those tagged sections (ensuring it wasn't changed when soup did cleanups)
    # from the post and returns that purged post and the purged sections.

    soup = BeautifulSoup(post, "html.parser")
    DNAs = soup.find_all("dna")

    purged = []

    # Needed in the case that <dna> contains another dna.
    original = post

    for dna in DNAs:
        raw_dna = re.escape(str(dna))

        # Need to fix indenting in html issues
        pretty_dna = "\s*" + re.escape(dna.prettify()).replace("\n", "\n\s*")

        # Soup often transforms html but shouldn't have here.
        for text in [raw_dna, pretty_dna]:
            match = re.search(text, original)
            if match:
                post = post.replace(match.group(), "", 1)

                print('\t REMOVED: "{}"'.format(match.group().replace("\n", "")))
                purged.append(dna.text)
                break
        else:
            assert False, ("Didn't find DNA to remove", post_name, dna)


    return post, " | ".join(purged)


def find_keyword_string (post, keyword, caseless = False):
    # finds and returns the string following keyword up to next BR_TAG
    # will remove any leading white space and embedded html tags

    if caseless:
        start = post.lower().find(keyword.lower())
    else:
        start = post.find(keyword)

    keyword_string = ''
    if start >= 0:    # found our tag;
        end = post.find(BR_TAG, start)
        assert end != -1, keyword + " string failed to terminate"
        keyword_string = post[start+len(keyword): end]
    return keyword_string


def get_blurb(post):
    # Remove (replace with empty) anything that looks like <b> <i> open or close (</b>) tag.
    # Should we do a more general replace of anything in <>?
    local_post = re.sub(
        r'</* *[bi] *>', '',
        post.lower()).strip()

    blurb = find_keyword_string(local_post, "Blurb:", True)
    if not blurb:
        blurb = find_keyword_string(local_post, "Blurb", True)
# TODO: some authors use summary for the blurb,
#   unfortunately, others use summary on subsequent posts to summarize situation so far...
#   so really can use "summary" only if don't already  have a blurb and we don't know that here.
#   if not blurb:
#       blurb = find_keyword_string(local_post, "Summary:", True)
#    if not blurb:
#        blurb = find_keyword_string(local_post, "Summary", True)
         # this could match something in the text but since we're not stripping it here, will go with it
    #if blurb:
        #print('\t Blurb: ' + blurb)
    return blurb


def format_new_post(title, author, post_date, post, is_final):
    # See ARCHIVE_TEMPLATE for template and layout

    with open(ARCHIVE_TEMPLATE) as template_file:
        template = template_file.read()

    story_data = STORY_TEMPLATE.format(
        jump_label="",
        date=post_date,
        body=post)

    #TODO Note that story_data might already contain the author's closing words,
    # if so, need to not duplicate them. Do a search in last ~100 chars of story body for the words in last

    closing_words = CLOSING_THE_END if is_final else CLOSING_TBC
    closing_section = STORY_STATUS_MARKER + closing_words + STORY_STATUS_MARKER_CLOSE

    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        .replace("$JUMP_SECTION", JUMP_TEMPLATE.format(jump_link=""))
        .replace("$POST_BODY_SECTION", story_data)
        .replace("$CLOSING_SECTION", closing_section)
        #NOTE Seth had put this backlink in to jump to the original post but Margaret and I don't like that
        #.replace("$OGLINK", '<a href="{}.html">originalpost</a><br/>'.format(msg_id))
        .replace("$COPYRIGHT_YEAR", post_date[:4]))

    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    print("\t wrote {}  chars to {}".format(
        len(new_story), output_name))

    return output_name

def cached_path(filename):
    return os.path.join(CACHE_DIRECTORY, filename)

def get_file(cached_filename, file_is_local, url = ''):
    # this finds, caches, and opens a copy of a file.
    # file_is_local asserts that we should find it in our cache because e.g. we just created it

    # Check if we already downloaded & saved locally
    cached_name = cached_path(cached_filename)

    if os.path.exists(cached_name):
        with open(cached_name, "r", encoding="utf-8") as cached:
            page_data = cached.read()

    else:
        #didn't find the file locally, should we have?
        assert not file_is_local, cached_name
        assert url.startswith("https:"), url

        #page_data = urllib.request.urlopen(url).read().decode("utf-8")
        request = urllib.request.urlopen(url)
        charset = request.info().get_content_charset("latin-1")
        page_data = request.read().decode(charset)

        page_data = html_cleanup(page_data)
        page_data = page_data.replace(
           '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
           '')
        with open(cached_name, "w", encoding="utf-8") as cached:
           cached.write(page_data)

        print("\t\tDownloaded: " + url)
        time.sleep(2)

    page_data = html_cleanup(page_data)
    return page_data


def get_post_msg_body(csv_line):
    # Fetch the body of the text from the post file
    # Any blurb will be extracted for return
    # and then any extranouse author notes will be stripped in here

    post_url = csv_line[post_url_index]
    print('\t fetching post url: "{}"'.format(post_url))
    msg_id = csv_line[msg_id_index]
    title = csv_line[title_index]

    fixed_post_fn = msg_id + ".soup.html"
    if not os.path.exists(cached_path(fixed_post_fn)):
        # Fix file at this time.
        original_post_fn = msg_id + ".html"
        if not os.path.exists(cached_path(original_post_fn)):
            # Download file
            assert get_file(original_post_fn, False, post_url)
            print ("\t\tCached {} => {}".format(post_url, original_post_fn))

        # Requires manual input to mark DNAs
        fix_one_file(original_post_fn)

    page_data = get_file(fixed_post_fn, file_is_local=True)

    # Fix an error by seth where tags must be lowercase.
    page_data = (page_data
        .replace('<DNA>', '<dna>')
        .replace('</DNA>', '</dna>')
        .strip())

    #print("\t page len:", len(page_data))
    #print("\t", page_data[0:40])

    # Phorum post files are pre-processed by story-fixer.py
    post_start_text = '<div class="message-body">'
    post_end_text = '</div>'

    assert page_data.startswith(post_start_text), (page_data[:100])
    assert page_data.count(post_end_text) >= 1
    assert page_data.endswith(post_end_text), (page_data[-100:],)

    blurb = get_blurb(page_data)

    post, comment_string = strip_comment(page_data, fixed_post_fn)

    lower = post.lower()
    for trigger in ["a/n", "<dna", "author's note"]:
        # These have to be manually cleaned up by editing some files.
        start = lower.find(trigger)
        assert start == -1, (fixed_post_fn, trigger, lower[start-10:start+10])

#   TODO print "manual inspect" warning.
#    for trigger in ["to be continued", "the end\W", "\Wfin\W"]:
#        assert not re.search(trigger, lower[-400:], re.I), (fixed_post_fn, trigger)

    # Remove <div> and then prune leading spaces + br tags at head/tail.
    post = strip_post_space(post[len(post_start_text):-len(post_end_text)])
    post = post_start_text + post + post_end_text

    # Aid in the readability of html files.
    chars_per_line = len(post) / (post.count("\n") + 1)
    if chars_per_line > 500:
        # Add artificial newlins to the post in the html file
        post = post.replace(BR_TAG, BR_TAG + "\n")

    return post, blurb


COPYRIGHT_PREFIX = '&copy; '        # code assumes these two prefixes are the same length so don't change!
OLD_COPYRIGHT_PREFIX = "&#169; "
ANOTHER_COPYRIGHT_PREFIX = '©'
COPYRIGHT_POSTFIX = ' Copyright held by the author.'

def find_existing_copyright(page_data):
    for C_PREFIX in [COPYRIGHT_PREFIX, OLD_COPYRIGHT_PREFIX, ANOTHER_COPYRIGHT_PREFIX]:
        start_text_index = page_data.rfind(C_PREFIX)
        if start_text_index > 0:
            return start_text_index
    assert start_text_index > 0, "source missing copyright statement"


def get_copyright(page_data):
    start_text_index = find_existing_copyright(page_data)
    end_text_index = page_data.rfind(COPYRIGHT_POSTFIX, start_text_index)
    assert start_text_index > 0 and end_text_index > 0
    assert end_text_index - start_text_index < 100, (start_text_index, end_text_index)
    copyright_text = page_data[start_text_index: end_text_index]
    return copyright_text


def update_copyright(page_data, post_date):
        text_copyright = get_copyright(page_data)
        year_match = re.search('[12][09][0-9][0-9]', text_copyright)
        assert year_match, text_copyright
        old_copyright_year = year_match.group()

        new_copyright_year = post_date[:4]
        #print("\t original copyright text: " + text_copyright + " new copyright " + new_copyright_year
        # the newly inserted copyright is going to look like this: "c YYYY [ - YYYY] Copyright held by the author."
        match = text_copyright.find(new_copyright_year)
        if match == -1:      # our date is not yet in the string,  append new date, overwriting any prexisting second year:
                updated_text_copyright = COPYRIGHT_PREFIX + old_copyright_year + " - " + new_copyright_year
                page_data = page_data.replace(text_copyright, updated_text_copyright)
                #print("\t\t new copyright string: " + updated_text_copyright)
        return page_data


def html_cleanup(page_data):
    # Safe, easy to apply HTML cleanups.

    # fixing <hr /> with or without spaces
    #(page_data, fixed_hrs) = re.subn(r"<hr[\s/]+>", "<hr>", page_data)
    #if fixed_hrs > 0:
    #    print("\tFixed {} HRs".format(fixed_hrs))

    # fix <p><hr></p> which is invalid because hr is a block level
    (page_data, fixed_end_p) = re.subn(r"(<p><hr[^>]*>)</p>", r"\1<p>", page_data)
    #if fixed_end_p > 0:
    #    print("\tFixed {} <p><hr></p>".format(fixed_end_p))

    # Make these uniform between new and old posts.
    (page_data, fixed_br) = re.subn(r"<br\s*.?>", BR_TAG, page_data)

    # TODO try out removing all </p> and see if visually different (will help out with some problems around <i>/<b>)
    # TODO try replacing 3+ br with 2.

    return page_data


def story_in_new_format(page_data, ignore_assert=True):
    if JUMP_LINK_INSERTION_MARKER not in page_data:
        assert ignore_assert
        return False

    # verify final 3 lines are
    #   STORY_STATUS_MARKER ...
    #   SEPERATOR_LINE
    #   &copy; (or similiar)

    story_status_index = page_data.find(STORY_STATUS_MARKER)
    if story_status_index < 0 or story_status_index < (len(page_data) - FINAL_SECTION_LENGTH_MAX):
        assert ignore_assert, (story_status_index, len(page_data))
        return False

    #TODO - commented these out until the closing duplication has been fixed:
#    assert 'To Be Continue' not in page_data[:story_status_index], page_data[story_status_index-100:]
#    assert 'The End' not in page_data[:story_status_index], page_data[story_status_index-100:]

    final_lines =  page_data[story_status_index:].split("\n")
    # All non-empty lines near the end of the file
    final_lines = [line.strip().lower() for line in final_lines if len(line.strip()) > 0]
    if not final_lines[0].startswith(STORY_STATUS_MARKER):
        assert ignore_assert, ("First line doesn't start with <span...story-insertion-marker closing-status...", final_lines)
        return False
    if final_lines[1] not in (SEPERATOR_LINE, "<p><hr /><p>"):
        assert ignore_assert, ("Second line was not " + SEPERATOR_LINE, final_lines)
        return False
    if not final_lines[2].startswith((COPYRIGHT_PREFIX, OLD_COPYRIGHT_PREFIX, ANOTHER_COPYRIGHT_PREFIX)):
        assert ignore_assert, ("Third line didn't start with any known copyright symbol", final_lines)
        return False
    return True


#This is called with archived files that we are going to append to
def ensure_new_story_format(file_name, page_data):
    if story_in_new_format(page_data):
        return page_data

    cache_name = cached_path(file_name.split(".", 1)[0] + ".cache.html")
    if os.path.exists(cache_name):
        with open(cache_name, encoding="utf-8") as f:
            return f.read()

    page_data = html_cleanup(page_data)

    # While MOVING_FAST_BREAKING_THINGS is turned on jump links and the story status marker will be incorrect.
    # We fix this by hand (opening and fixing each file) but this takes A LOT of time, so we avoid it by
    # using an approximating till we're ready for the final run.

    # This is the sloppy, doesn't work perfectly used for devel
    if MOVING_FAST_BREAKING_THINGS:
        # story might not be considered in new format by story_in_new_format but we have our own special check
        if JUMP_LINK_INSERTION_MARKER in page_data and STORY_STATUS_MARKER in page_data:
            return page_data

        page_data = page_data.replace("<hr>", "<hr><p>\n" + JUMP_LINK_INSERTION_MARKER + "\n",1)
        # should be above page seperator
        copyright_index = find_existing_copyright(page_data)
        page_date = page_data[:copyright_index] + \
            "\n" + STORY_STATUS_MARKER + STORY_STATUS_MARKER_CLOSE + "\n" + \
            page_data[copyright_index:]
        return page_date

    # Human is responsible for this editing of archived files:
    #   1. Moving the JUMP_LINK_INSERTION_MARKER to the correct point (after others or after navigations or after author name)
    #       a. If no pre-existing navigate / jump section add a following SEPERATOR_LINE (<p><hr></p>)
    #   2. Moving STORY_STATUS_MARKER at end up to precede copyright and it's hr
    #       a. Move any existing <font>...To Be Continued...</font> from post body to inside the closing span
    #           (this author provided story status info can actually be deleted 'cause the code will later!)
    #   3. Verifying STORY_STATUS_MARKER, SEPERATOR_LINE, &copy all in consecutive lines before final boilerplate

    # Need for linux counts to work.
    if IS_LINUX:
        page_data = page_data.replace("\r\n", "\n")

    # Open the file and let human move the markers to the right place
    write_data = "\n".join([
        JUMP_LINK_INSERTION_MARKER,
        page_data,
        STORY_STATUS_MARKER + STORY_STATUS_MARKER_CLOSE + "\n", # makes selection easier
    ])

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
        temp_file_path = f.name
        # write links that need to be inserted into an existing story
        # followed by the existing story html
        f.write(write_data)

    # Open the file for human processing
    if IS_LINUX:
        subprocess.check_output(["gedit", temp_file_path])
    else:
        subprocess.check_output(["notepad.exe", temp_file_path])

    with open(temp_file_path, encoding="utf-8") as f:
        new_data = f.read().strip()

    # if 1a then <p><hr></p> adds ~15 characters
    # Make sure no more than 30 characters were added to the file.
    assert len(write_data) + 30 >= len(new_data) > len(page_data), (len(write_data), len(new_data), len(page_data))

    os.unlink(temp_file_path)

    assert not new_data.startswith(JUMP_LINK_INSERTION_MARKER), "You forgot to move the jump marker!"
    assert not new_data.endswith(STORY_STATUS_MARKER_CLOSE), "You forgot to move the stuff at the bottom"
    assert story_in_new_format(new_data, ignore_assert=False)

    # Cache new format file.
    with open(cache_name, "w", encoding="utf-8") as f:
        f.write(new_data)

    return new_data


CURRENT_STORY_STATUS_RE = re.compile(
    re.escape(STORY_STATUS_MARKER) +
    "(.{0,100})" +
    re.escape(STORY_STATUS_MARKER_CLOSE))

# This is used to update the story ending status of all files created in here.
#TODO: it needs to take into account that the author may have provided a closing of their own in the post.
def change_story_status(page_data, is_final):
    current = CURRENT_STORY_STATUS_RE.search(page_data)
    assert current, "We didn't find STORY_STATUS_MARKER!"

    new_status = CLOSING_THE_END if is_final else CLOSING_TBC
    #print('\tChanging status from "{}" to "{}"'.format(current.group(1), new_status))

    return page_data.replace(
        current.group(0), # The entire match STORY_STATUS_MARKER + current_text + STORY_STATUS_MARKER_CLOSE
        STORY_STATUS_MARKER + new_status + STORY_STATUS_MARKER_CLOSE)

    #TODO: after the replace, but before the return,
    # do a lower case search of the 70 chars before the STORY_STATUS_MARKER for {To Be Continued, The End, Fin}
    #if not found, return
    #if found, have the human take corrective action either substituting the author's for ours OR deleting it.

########## MAIN ##############


if not os.path.exists("cache"):
        os.makedirs("cache")

with open(INPUT_CSV_PATH, encoding='utf-8') as csv_file:
    csv_reader = csv.reader(csv_file)
    csv_input = list(csv_reader)

print("Archiving Dwiggie posts from: ", INPUT_CSV_PATH);
print("Number of rows: {}, number of columns: {}".format(
    len(csv_input), len(csv_input[0])))
print()

header = csv_input.pop(0)

# Join each item in the list with ', ' and print
print("Column Headers:")
print(", ".join(header))
#print()

# Verify important column assumptions
assert header[post_date_index] == "last_update/Posting"
assert header[msg_id_index] == "Msg Id"
assert header[author_index] == "author_name"
assert header[title_index] == "title_name"
assert header[action_index] == "action"
assert header[category_index] == "category"
assert header[post_url_index] == "new posting - real url"
assert header[archive_url_index] == "archive real url"
assert header[final_post_index] == "FinalPost?"
assert header[which_book_index] == "Book"
assert header[blurb_index] == "Blurb"
assert header[short_url_index] == "URL"

# Remove any extraneous entries at end of list (defined as ones that don't have good looking dates):
while not ('200' in csv_input[-1][0] or '199' in csv_input[-1][0]):
    # remove the last line :)
    dropped = csv_input.pop()
    #print("Dropping:", ",".join(dropped))

csv_output = {}     # this file goes back to Margaret tracking what has happened
csv_output["header"] = header + ["New Filename"]
tbd_output = []     # this file will need to be processed by human and then csv_output file manually updated
tbd_output.append(header + ["New Filename"])

if DOWNLOAD_FIRST:
    # Download all forum messages for story_fixer.py
    for i, csv_line in enumerate(csv_input):
        assert len(csv_line) == len(header), (len(header), csv_line)

        action = csv_line[action_index]
        msg_id = csv_line[msg_id_index]

        if action in ("Amend", "ArchiveNew", "AppendNew", "AppendArchive"):
            post_url = csv_line[post_url_index]
            post_name = msg_id + ".html"
            assert get_file(post_name, False, post_url)
            print ("\t\tCached {} => {}".format(post_url, post_name))
    print("\nFiles fetched. Now run story extractor, then toggle DOWNLOAD_FIRST and rerun story archiver\n")
    sys.exit()

toAmend = 0
archivedNew = 0
appendedNew = 0
appendedArchive = 0
for i, csv_line in enumerate(csv_input):
    # Verify this line has correct number of columns
    assert len(csv_line) == len(header), (len(header), csv_line)

    action = csv_line[action_index]
    category = csv_line[category_index]    #note that this value could be null
    msg_id = csv_line[msg_id_index]
    #TODO: we need to ensure that we don't duplicate the author's closing - we have duplicate "The End"s
    is_final = csv_line[final_post_index].lower().startswith('y')

    # Archived entries shouldn't have a action:
    if msg_id != "":
        assert action != "", (i+2, action)

    if action == "":
        continue

    post_date = csv_line[post_date_index]
    author = csv_line[author_index]
    temp_title = csv_line[title_index]
    # Title needs to be stripped of any excess verbiage, this assumes that
    # CSV has been groomed to insert '::' at end of simple title
    title_delimiter = '::'
    temp_index = temp_title.find(title_delimiter)    # returns -1 if not found
    if temp_index > 0:
        title = temp_title[:temp_index]
    else:
        title = temp_title

    if action == "Amend":
        post_url = csv_line[post_url_index]
        page_data = get_file(msg_id + ".html", False, post_url)
        #NOTE: have no way to know which file (archived or new) is being amended, so let human fetch both the post and archived text
        #or could groom the csv to include the correct info...
        print('Amendment({}) - ***** HUMAN INTERVENTION required: "{}"  {} modify file and update CSV'.format(i+2, post_date, title))

        #Save all the data about this story so human can copy it to csv_output when amendment is complete:
        tbd_line = csv_line[:last_csv_input_index+1] + ["TBD"]     #we don't have a file to modify, human will have to add it.
        tbd_line[title_index] = title
        tbd_line[post_date_index] = csv_line[post_date_index]
        tbd_line[final_post_index] = csv_line[final_post_index]
        tbd_output.append(tbd_line)
        toAmend += 1
        continue

    elif action == "ArchiveNew":

        if ONLY_A_FEW and archivedNew >= 2:
            continue

        print('ArchiveNew({}): "{}"'.format(i+2, title))
        message_body, blurb = get_post_msg_body(csv_line)
        new_filename = format_new_post(
            title, author,
            post_date, message_body,
            is_final)

        #TODO - there was the case that the first entry was a dna, are there other cases?
        assert title not in csv_output or csv_output[title][action_index] == 'dna', (title, csv_output[title])

        #Save all the (new) data about this story (use stripped title) and the file (stripped of it's path name) where the new story resides:
        if blurb:
            csv_line[blurb_index] = blurb
        else:
            if not csv_line[blurb_index]:
                csv_line[blurb_index] = "tbd"

        csv_output[title] = csv_line[:last_csv_input_index+1] + [new_filename[len(CACHE_DIRECTORY):]]
        csv_output[title][title_index] = title
        csv_output[title][creation_date_index] = csv_line[post_date_index]
        #print(csv_output[title])

        archivedNew += 1

    elif action == "AppendNew":
         #In this case, we know the format of the file and thus are free to shove stuff into it without care.

        if ONLY_A_FEW and appendedNew >= 1:
            continue

        print('AppendNew({}): {}'.format(i+2, title))

        #fetch post text to append to file created previously during this archive:
        message_body, blurb = get_post_msg_body(csv_line)
        if blurb:
            if csv_line[blurb_index]:
                print("\tFOUND NEW BLURB: ")
            csv_line[blurb_index] = blurb

        #find the relevant file to append to which should now have an entry in the output CSV from previous post
        if title not in csv_output: # see if it is there caseless and if so, correct current titles to match saved title
            matches = [csv_output[key] for key in csv_output if str_equal(key, title)]
            assert len(matches) == 1, (title, matches)
            title = csv_line[title_index] = matches[0][title_index]
        assert title, "Appending to non-existent story!"
        insertion_file = csv_output[title][to_archive_filename_index]
        page_data = get_file(insertion_file, True)

        print('\t from {} into {}'.format(title, insertion_file))

        # find the insertion point:
        insertion_index =  page_data.rfind(STORY_INSERTION_MARKER)
        #print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
        #print("\t", "{} characters copied, {:.1f}% of new file".format(len(message_body), 100 * len(message_body) / len(page_data)))
        assert insertion_index

        # deal with To Be Continued and The End
        page_data = change_story_status(page_data, is_final)

        #We don't add jump links for these because no one has yet read this non-existant file!
        story_data = STORY_TEMPLATE.format(jump_label='', date=post_date, body=message_body,)
        #TODO: verify that the correct white space gets inserted between posts.
        page_data = page_data.replace(STORY_INSERTION_MARKER,
                                      story_data + "\n" + STORY_INSERTION_MARKER)

        page_data = update_copyright(page_data, post_date)

        output_file = cached_path(insertion_file)
        with open(output_file, "w", encoding="utf-8") as output_file:
            output_file.write(page_data)

        #update any necessary story data
        csv_output[title][post_date_index] = csv_line[post_date_index]
        csv_output[title][final_post_index] = csv_line[final_post_index]

        appendedNew += 1
        continue

    elif action == "AppendArchive":

        if ONLY_A_FEW and appendedArchive >= 2:
            continue

        print('AppendArchive({}): {}'.format(i+2, title))

        #fetch post text to append to archived file:
        message_body, blurb = get_post_msg_body(csv_line)
        if blurb:
            print("\tFOUND NEW BLURB: ")
            csv_line[blurb_index] = blurb

        #Determine the correct associated archive file to fetch - should be first CSV entry with matching title:
        archive_url = ''
        for j, test_line in enumerate(csv_input):
           if str_equal(test_line[title_index], title):
               #title alone is insufficient, test author name too but remember that author string isn't always exact match!
               if (test_line[author_index] != csv_line[author_index] and
                       loose_equal(test_line[author_index], csv_line[author_index])):
                   print("\tERROR: appending with non-matching author names: {} {}):".format(csv_line[author_index], test_line[author_index]))
                   assert False
               archive_url = test_line[archive_url_index]
               print('\t Appending to: {}'.format(archive_url))
               break
        assert archive_url
        #print('Appending({}): ***** ERROR: no archive file for {}'.format(i+2, csv_line[title_index]))

        # find the insertion file, going to hope they all have same basic format at end!
        # Note: because the local cache is searched first, multiple calls to append archive will magically work correctly!
        start_indx = archive_url.rfind("/")
        insertion_filename = archive_url[start_indx+1:]
        page_data = get_file(insertion_filename, False, archive_url)
        page_data = ensure_new_story_format(insertion_filename, page_data)

        #TODO: this is temp code to make styles look correct in local work, remove before done:
        page_data = page_data.replace('/style/stories.css', 'style/stories.css')
        page_data = page_data.replace('/derby/back.gif', 'derby/back.gif')

        charset_info = page_data.find('<meta charset="utf-8">')
        if charset_info < 0:
            page_data = page_data.replace('<head>', '<head>\n <meta charset="utf-8"> \n')

        #search for and remove deprecated author addrs: <!--mailto: apterja@optusnet.com.au -->
        page_data = re.sub(r'<!--mailto:.{1,50} -->', '', page_data, re.I)

        #insert the jump links first:
        jump_post_date = datetime.datetime.strptime(post_date, "%Y-%m-%d")
        jump_date_str = jump_post_date.strftime('%A %B %d, %Y')

        jump_new_date = post_date.replace("-", "")
        jump_string = '\n<a href="#new{}">Jump to new as of {}</a><br/>'.format(
            jump_date_str, jump_date_str)

        jump_label = '<a id="new{}"></a>'.format(jump_date_str)

        assert JUMP_LINK_INSERTION_MARKER in page_data, "should have been tested"
        assert STORY_INSERTION_MARKER in page_data, "see above line"

        if jump_string in page_data and jump_label in page_data:
            print("\tAppend already performed (already found {})".format(jump_label))
        else:
            # remove any story_status from existing file and append correct status to end of new:
            page_data = change_story_status(page_data, is_final)

            insertion_index =  page_data.index(STORY_INSERTION_MARKER)
            #print("\t insert location: {} in {} length file ({} from end)".format(
            #    insertion_index, len(page_data), insertion_index - len(page_data)))
            #print("\t {} characters copied, {:.1f}% of new file".format(
            #    len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index and insertion_index > (len(page_data)- FINAL_SECTION_LENGTH_MAX)

            story_data = STORY_TEMPLATE.format(
                jump_label=jump_label + "\n",
                date=post_date,
                body=message_body)

            if JUMP_SECTION in page_data and (JUMP_SECTION + SEPERATOR_LINE) not in page_data:
                # To avoid double <hr> in new stories with no jump links we avoid adding the <hr>
                # till the first append, but only add it the 1st append.
                page_data = page_data.replace(JUMP_SECTION, JUMP_SECTION + SEPERATOR_LINE)

            new_page_data = (page_data
                .replace(JUMP_LINK_INSERTION_MARKER, jump_string + "\n" + JUMP_LINK_INSERTION_MARKER)
                .replace(STORY_INSERTION_MARKER, story_data + "\n" +  STORY_INSERTION_MARKER)
            )

            new_page_data = update_copyright(new_page_data, post_date)

            output_file = cached_path(insertion_filename)
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(new_page_data)

        #TODO: should we copy the entire csv_line?
        if title not in csv_output:     # start with the archived story data
            #print('\tAdding title to csv output', title)
            csv_output[title] = test_line[:last_csv_input_index+1] + [insertion_filename]
            csv_output[title][action_index] = csv_line[action_index]
            csv_output[title][category_index] = csv_line[category_index]

        csv_output[title][post_date_index] = csv_line[post_date_index]
        csv_output[title][final_post_index] = csv_line[final_post_index]

        if blurb:
            csv_output[title][blurb_index] = blurb


        appendedArchive += 1
        continue

    elif action == "no-op":
        #these are extraneous posts, for example, previously processed posts,
        # ignore here, but they will get archived from forum

        #print('No-op({}): "{}" by {}'.format(i+2, title, author))
        continue
    elif action == "delete":
        #garbage post that is ignored here and deleted from forum
        print('Delete this post({}): "{}" by {}'.format(i+2, title, author))
        if title not in csv_output:
            csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
        continue
    elif action == "dna":
        #Do Not Archive, so, duh, do nothing here, do they get removed from forum archive?
        print('DNA this post({}): "{}" by {}'.format(i+2, title, author))
        if title not in csv_output:
            csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
        continue
    else:
        print("unhandled action:", action)

# Quick validation that each key appears only once in csv_output
key_counts = Counter([key.lower() for key in csv_output.keys()])
for key, count in key_counts.most_common():
    if count > 1:
        print ("**ERROR** Title duplicated in csv:",
               [dupe for dupe in csv_output.keys() if str_equal(key, dupe)])
        assert False

try:
    with open(OUTPUT_CSV_PATH, "w", newline='') as csv_file:
       writer = csv.writer(csv_file)
       writer.writerows(csv_output.values())

    with open(OUTPUT_CSV_PATH + '.tbd.csv', "w", newline='') as tbd_file:
       writer = csv.writer(tbd_file)
       writer.writerows(tbd_output)


except IOError:
    print("I/O error")

# len - 1 is for the header line.
print("""
Archive complete:
    {} story files created
    {} Amendments must be completed manually (see log or CSV file)
    {} New Stories (with {} Updates to those)
    {} Archive Updates ({} stories)""".format(
    len(csv_output)-1, toAmend, archivedNew, appendedNew,
    appendedArchive, (len(csv_output)-1-archivedNew)))
