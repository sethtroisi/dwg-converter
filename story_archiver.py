# -*- coding: utf8 -*-
import csv
import json
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
#import pdb

from story_fixer import fix_one_file

#-----------------------

# TODO: toggle these off for production run
PRE_PRODUCTION = False
ONLY_A_FEW = False
MOVING_FAST_BREAKING_THINGS = False
    #do we need to run one complete run with this to True in to format any historical files for appendarchive?

#-----------------------

ARCHIVE_TEMPLATE = "templates/story_archive_template.html"
CACHE_DIRECTORY = "cache/"      #both inbound and outbound files end up here

#------------------------

INPUT_CSV_FILENAME = "data/modified_dwg_index.csv"  # output from csv_creator and manually completed
OUTPUT_CSV_FILENAME = "data/dwg_archive_results.csv"
input_csv_filename = ""
output_csv_filename = ""

#----------------
#This section of info must jibe with that in the csv_creator program:

#TODO:
PREVIOUS_ARCHIVE_DATE = datetime.datetime(2019,7,1)	# will ignore any messages older than this as they've already been processed
CURRENT_ARCHIVE_DATE = datetime.datetime(2021, 9,7)    
	# this is the final date included in this archive, becomes next "PREVIOUS_ARCHIVE_DATE"
comparison_date = int(PREVIOUS_ARCHIVE_DATE.timestamp())

MSG_BOARD_FORUM_ID = "5"
ANI_MSG_FORUM_ID = "6"
TOP_LEVEL_MSG = "0"

#Input CSV file should have the following columns with names specified in main below:
post_date_index = 0
creation_date_index = 1
msg_id_index = 2
author_index = 3
title_index = 4
action_index = 5
final_post_index=6
category_index = 7
post_url_index = 8
archive_url_index = 9
northanger_index = 10
sense_index = 11
pride_index = 12
emma_index = 13
mansfield_index = 14
persuasion_index = 15
juvenilia_index = 16
misc_index = 17
author_id_index = 18
email_index = 19
blurb_index=20
last_csv_input_index=20

#The output CSV file will have the same columns as input (previous list) plus this immediately after:
to_archive_filename_index=last_csv_input_index+1

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
  <hr><br/>
  {jump_label}\n<i>Posted on {date}</i><br/><br/>
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
DIV_END_TAG = "</div>"

EMPTY_LINE = "<p>"
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

    hr_br_or_space = r'(\s*<[bh]r\s*/?>\s*)\+' 
    data = re.sub(r'^' + hr_br_or_space, '', data)
    data = re.sub(hr_br_or_space + r'$', '', data)
    return data


def strip_comment(post, post_name):
    # Use this after story_fixer.py which will embed each DNA section in a DNA tag
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
                #print('\t REMOVED: "{}"'.format(match.group().replace("\n", "")))
                assert len(dna.text) < 2500, (len(dna.text), dna.text, post_name)
                purged.append(dna.text)
                break
        else:
            assert False, ("Didn't find DNA to remove", post_name, dna)

    return post.strip(), " | ".join(purged)


def find_keyword_string (post, keyword, caseless = False):
    # finds and returns the string following keyword up to next BR_TAG

    if caseless:
        start = post.lower().find(keyword.lower())
    else:
        start = post.find(keyword)

    keyword_string = ''
    if start >= 0:    # found our tag;
        end = post.find(BR_TAG, start)
        #Hack: doesn't find end if blurb is final item in the post - iwc, should be followed by "</div>" or our marker, "</dna>"
        if end ==-1:
            end = post.find("</", start)
        assert end != -1, keyword + " string failed to terminate"
        keyword_string = post[start+len(keyword): end]
    return keyword_string


def get_blurb(post):
    # unfortunately, some authors use 'summary' for the blurb,
    # but others use summary on subsequent posts to summarize situation so far...
    # so can't rely on "summary" as a keyword.Have manually handle those: for all empty
    # blurbs in the output CSV, /generate text and store it in the input CSV, then rerun archiver.

    # Remove (replace with empty) anything that looks like <b> <i> open or close (</b>) tag.
    # Should we do a more general replace of anything in <>?
    local_post = re.sub(
        r'</* *[bi] *>', '',
        post.lower()).strip()
  
    blurb = find_keyword_string(local_post, "Blurb", True)
    blurb = blurb.strip(" \n:")   #sometimes there is a ':' or a ' :' or even '\n :' after 'blurb'     
    return blurb


def format_new_post(title, author, post_date, post, is_final):
    # See ARCHIVE_TEMPLATE for template and layout

    with open(ARCHIVE_TEMPLATE, encoding='utf-8') as template_file:
        template = template_file.read()

    jump_link_string, jump_label = create_jump_lines(post_date, msg_id)
    #TODO 2019: for now, make jump links invisible in new stories but maybe rethink this:
    jump_link_string = '<!-- ' + jump_link_string +' -->'
    story_data = STORY_TEMPLATE.format(
        jump_label=jump_label,
        date=post_date,
        body=post)

    closing_words = CLOSING_THE_END if is_final else CLOSING_TBC
    closing_section = STORY_STATUS_MARKER + closing_words + STORY_STATUS_MARKER_CLOSE

    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        .replace("$JUMP_SECTION", JUMP_TEMPLATE.format(jump_link=jump_link_string))
        .replace("$POST_BODY_SECTION", story_data)
        .replace("$CLOSING_SECTION", closing_section)
        #TODO:Figure out how to make this conditional inside the template. possible?
                 #comment out these lines for production run, and in append archive below
        #if PRE_PRODUCTION:
            # note that the stories.css contains it's own pointer which doesn't work hence the modified copy
        #    .replace('/style/stories.css', '../templates/stories (for local use only).css')
        #    .replace('/derby/back.gif', '../templates/back.gif')  
        #NOTE Seth had put this backlink in to jump to the original post but Margaret and I don't like that
        #.replace("$OGLINK", '<a href="{}.html">originalpost</a><br/>'.format(msg_id))
        .replace("$COPYRIGHT_YEAR", post_date[:4]))

    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    print("\t wrote to {}".format(output_name))

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
    # an then any extranous author notes will be stripped in here

    post_url = csv_line[post_url_index]
    msg_id = csv_line[msg_id_index]
    title = csv_line[title_index]
    #print('\t processing: "{}"'.format(msg_id))
    
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
    
    #look for blurb before it might get stripped with comments
    blurb = get_blurb(page_data)

    # assure that all dna's come out of story_fixer in lc.
    assert '<DNA>' not in page_data, "assumed incorrectly, convert these to lowercase"

    # Phorum post files are pre-processed by story-fixer.py
    post_start_text = '<div class="message-body">'
    post_end_text = '</div>'

    post, comment_string = strip_comment(page_data, fixed_post_fn)

    lower = post.lower()
    for trigger in ["a/n", "<dna", "author's note"]:
        # These have to be manually cleaned up by editing some files.
        start = lower.find(trigger)
        assert start == -1, (fixed_post_fn, "must remove: ", trigger, lower[start-10:start+10])

#    need to look for author provided ending status.
#    Now assume that Human will clean that up in story fixer step previous to here
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
    # BLT 2019: status?

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

    #commented these out until the closing duplication has been fixed - is this now working again??:
    assert 'To Be Continued' not in page_data[:story_status_index], page_data[story_status_index-100:]
    assert 'The End' not in page_data[:story_status_index], page_data[story_status_index-100:]

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


#This is called with archived files that we are going to append to.
# If we've not seen this file before, we need to "fix" its format. Do so manually in editor and then cache that copy. 
def ensure_new_story_format(file_name, page_data):

    BYTE_ORDER_MARK = "ï»¿"
    #this gets inserted by some editors, such as Notepad. I mistakenly added at least one in prev archive
    start = page_data.find(BYTE_ORDER_MARK)
    if start == 0:    # found our tag;
        page_data = page_data[len(BYTE_ORDER_MARK):]
       
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

    # Human is responsible for this editing of archived files (these rules are very particularly enforced above in story_in_new_format:
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
        subprocess.check_output(["gedit", "--new-window", "--wait", temp_file_path])  
    else:
        subprocess.check_output(["notepad.exe", temp_file_path])

    with open(temp_file_path, encoding="utf-8") as f:
        new_data = f.read().strip()

    # if case 1a above then <p><hr></p> adds ~15 characters
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
# author may have provided a closing of their own in the post but human should have removed that in story fixer step
def change_story_status(page_data, is_final):
    current = CURRENT_STORY_STATUS_RE.search(page_data)
    assert current, "We didn't find STORY_STATUS_MARKER!"

    new_status = CLOSING_THE_END if is_final else CLOSING_TBC
    #print('\tChanging status from "{}" to "{}"'.format(current.group(1), new_status))

    return page_data.replace(
        current.group(0), # The entire match STORY_STATUS_MARKER + current_text + STORY_STATUS_MARKER_CLOSE
        STORY_STATUS_MARKER + new_status + STORY_STATUS_MARKER_CLOSE)

    #TODO 2019: should we do a lower case search of the 70 chars before the STORY_STATUS_MARKER
    # for {To Be Continued, The End, Fin}
    # currently relying on manual preprocessing to avoid duplication?

def create_jump_lines(post_date, msg_id):
    #creates html for jump_link_string to "take" reader to jump_label
    JUMP_LABEL_TEXT = '<a id="new{}-{}"></a>'
    JUMP_LINK_STRING_TEXT = '<a href="#new{}-{}">Jump to new as of {}</a><br/>'
    jump_post_date = datetime.datetime.strptime(post_date, "%Y-%m-%d")
    jump_date_str = jump_post_date.strftime('%A %B %d, %Y')
    jump_new_date = post_date.replace("-", "")
    jump_link_string = JUMP_LINK_STRING_TEXT.format(
        post_date, msg_id, jump_date_str)
    jump_label = JUMP_LABEL_TEXT.format(post_date, msg_id)
    return jump_link_string, jump_label


########## MAIN ##############


if not os.path.exists("cache"):
        os.makedirs("cache")

input_csv_filename = input("Specify manually edited CSV action file (default:{}):  ".format(INPUT_CSV_FILENAME))
if input_csv_filename == "":
    input_csv_filename = INPUT_CSV_FILENAME
output_csv_filename = input("Specify Output CSV file (default:{}):  ".format(OUTPUT_CSV_FILENAME))
if output_csv_filename == "":
    output_csv_filename = OUTPUT_CSV_FILENAME
output_tbd_filename = output_csv_filename + '.tbd.csv'

with open(input_csv_filename, encoding='utf-8') as csv_file:
    csv_reader = csv.reader(csv_file)
    csv_input = list(csv_reader)

print("\nArchiving Dwiggie posts since {} from: {}\n".format(PREVIOUS_ARCHIVE_DATE, input_csv_filename))
print("Number of rows: {}, number of columns: {}".format(len(csv_input), len(csv_input[0])))
print()

header = csv_input.pop(0)

# Join each item in the list with ', ' and print
#print("Column Headers:")
#print(", ".join(header))
#print()

# Verify important column assumptions
assert header[post_date_index] == "last_update/Posting"
assert header[msg_id_index] == "Msg Id"
assert header[author_index] == "author_name"
assert header[title_index] == "title_name"
assert header[action_index] == "action"
assert header[final_post_index] == "FinalPost?"
assert header[category_index] == "category"
assert header[post_url_index] == "posting - real url"
assert header[archive_url_index] == "archive real url"
assert header[northanger_index] == "northanger"
assert header[sense_index] == "sense"
assert header[pride_index] == "pride"
assert header[emma_index] == "emma"
assert header[mansfield_index] == "mansfield"
assert header[persuasion_index] == "persuasion"
assert header[juvenilia_index] == "juvenilia"
assert header[misc_index] == "misc"
assert header[blurb_index] == "Blurb"
assert header[email_index] == "email"

IMPORTANT_ACTIONS = ("Amend", "ArchiveNew", "AppendNew", "AppendArchive")

# Remove any extraneous entries at end of list (defined as ones that don't have good looking dates):
while not csv_input[-1][post_date_index].startswith(('20','199')):
    # remove the last line :)
    dropped = csv_input.pop()
    #print("Dropping:", ",".join(dropped))

csv_output = {}     # this will specify all the actions to take at dwiggie
csv_output["header"] = header + ["New Filename"]
tbd_output = []
   # this file holds all the non "ArchiveNew", "AppendNew", "AppendArchive entrys and
   # must be processed by a human. In case of Amend, csv_output file may need to be manually updated as a result
tbd_output.append(header + ["New Filename"])

download_first = ""
while download_first not in ("y", "n"):
    download_first = input("Are there post files to download? (y/n)")

if download_first == 'y':

    # Download all forum messages for story_fixer.py
    for i, csv_line in enumerate(csv_input):
        assert len(csv_line) == len(header), (len(header), csv_line)

        action = csv_line[action_index]
        msg_id = csv_line[msg_id_index]

        if action in IMPORTANT_ACTIONS:
            post_url = csv_line[post_url_index]
            post_name = msg_id + ".html"
            assert get_file(post_name, False, post_url)
#            print ("\t\tCached {} => {}".format(post_url, post_name))
print()

toAmend = 0
archivedNew = 0
appendedNew = 0
appendedArchive = 0
deleteCount = 0
extraneousActions = 0

for i, csv_line in enumerate(csv_input):
    # Verify this line has correct number of columns
    assert len(csv_line) == len(header), (len(header), csv_line)

    action = csv_line[action_index]
    category = csv_line[category_index]
    if action in IMPORTANT_ACTIONS and not (category in ("Epi", "Fant", "ANI")):
        print ("\t\Missing Category Value: ({}) ".format(i, csv_line[title_index]))

    msg_id = csv_line[msg_id_index]
    is_final = csv_line[final_post_index] == "1"

    # Archived entries shouldn't have a action:
    if msg_id != "":
        assert action != "", (i+2, action)

    if action == "":
        continue

    #TODO marker and conditional for debugging breakpoint:
    #if msg_id == "specify message id here": 
    #   print("This is a Message with a problem")
    #else:
    #    continue
    
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
        page_data = get_file(msg_id + ".html", False, post_url) #fetch file so have text editor access to it.
        #NOTE: have no way to know which file (archived or new) is being amended, so let human figure it out.
        # May involve manually fetching an archived story file and modifying it.
        print('''\nAMENDMENT({}) - ***** HUMAN INTERVENTION required: "{}"
              {} modify file and update CSV\n'''.format(i+2, post_date, csv_line[title_index]))

        #Save all the data about this story so human can copy it to csv_output when amendment is complete:
        tbd_line = csv_line[:last_csv_input_index+1] + ["TBD"]     #we don't have a file to modify, human will have to add it.
        tbd_output.append(tbd_line)
        toAmend += 1
        continue

    elif action == "ArchiveNew":

        if ONLY_A_FEW and archivedNew >= 5:
            continue

        print('ARCHIVE NEW({}): "{}"  id {}'.format(i+2, title, msg_id))
        #TODO 2019  we could check whether file already exists before doing the work but no harm
        message_body, blurb = get_post_msg_body(csv_line)
        new_filename = format_new_post(
            title, author,
            post_date, message_body,
            is_final)

        #might have a previous entry which is no-op or dna or other, that is okay
        assert ((not title in csv_output) or
                (csv_output[title][action_index] in ["dna", "delete", "amend", "no-op"])), (title, csv_output[title])

        #Save the (new) story data (use stripped title) and the file (stripped of it's path name) where the new story resides:
        if blurb:   # save any new blurb over whatever might be in the input csv:
            csv_line[blurb_index] = blurb
            #print("blurb: " + csv_line[blurb_index])
        else:   # use any csv content else provide placeholder
            if not csv_line[blurb_index]:
                csv_line[blurb_index] = "tbd"

        csv_output[title] = csv_line[:last_csv_input_index+1] + [new_filename[len(CACHE_DIRECTORY):]]
        csv_output[title][title_index] = title
        csv_output[title][creation_date_index] = csv_line[post_date_index]

        archivedNew += 1

    elif action == "AppendNew":
         #In this case, we know the format of the file and thus are free to shove stuff into it without care.

        if ONLY_A_FEW and appendedNew >= 5:
            continue

        print('APPEND NEW({}): {}  id {}'.format(i+2, csv_output[title][title_index], msg_id))

        #fetch post text to append to file created previously during this archive:
        message_body, blurb = get_post_msg_body(csv_line)

        if blurb:
            if csv_output[title][blurb_index]:
                print("\tFOUND NEW BLURB: " + blurb)
            csv_output[title][blurb_index] = blurb

        #find the relevant file to append to which should now have an entry in the output CSV from previous post
        if title not in csv_output: # see if it is there caseless and if so, correct current titles to match saved title
            #TODO 2020: should disambiguate any duplicate titles via author name, but will wait til that happens...
            matches = [csv_output[key] for key in csv_output if str_equal(key, title)]
            assert len(matches) == 1, (title, matches, "stories of same name, add duplication handling to code!")  
            title = csv_line[title_index] = matches[0][title_index]
        assert title, "Appending to non-existent story!"
        insertion_file = csv_output[title][to_archive_filename_index]
        page_data = get_file(insertion_file, True)

        print('\t into {}'.format(insertion_file))

        # find the insertion point:
        insertion_index =  page_data.rfind(STORY_INSERTION_MARKER)
        #print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
        #print("\t", "{} characters copied, {:.1f}% of new file".format(len(message_body), 100 * len(message_body) / len(page_data)))
        assert insertion_index

        # deal with To Be Continued and The End
        page_data = change_story_status(page_data, is_final)

        #Add jump labels:
        jump_link_string, jump_label = create_jump_lines(post_date, msg_id)
        #TODO 2019: for now, make jump links invisible but maybe rethink this:
        jump_link_string = '<!-- ' + jump_link_string +' -->'
        story_data = STORY_TEMPLATE.format(jump_label=jump_label, date=post_date, body=message_body,)
        #this is where the white space gets inserted between posts
        new_page_data = (page_data
            .replace(JUMP_LINK_INSERTION_MARKER, jump_link_string +'\n' + JUMP_LINK_INSERTION_MARKER)
            .replace(STORY_INSERTION_MARKER, EMPTY_LINE + EMPTY_LINE + story_data + "\n" +  STORY_INSERTION_MARKER)
            )

        new_page_data = update_copyright(new_page_data, post_date)

        output_file = cached_path(insertion_file)
        with open(output_file, "w", encoding="utf-8") as output_file:
            output_file.write(new_page_data)

        #update any necessary story data
        csv_output[title][post_date_index] = csv_line[post_date_index]
        csv_output[title][final_post_index] = csv_line[final_post_index]

        appendedNew += 1
        continue

    elif action == "AppendArchive":

        if ONLY_A_FEW and appendedArchive >= 2:
            continue

        print('APPEND ARCHIVE({}): {} id {}'.format(i+2, title, msg_id))

        #fetch post text to append to archived file:
        message_body, blurb = get_post_msg_body(csv_line)
        if blurb:
            print("\tFOUND NEW BLURB: " + blurb)
            #blurb will get saved to the output_csv when we find the appropriate entry below

        #Determine the correct associated archive file to fetch:
        archive_url = ''
        for j, test_line in enumerate(csv_input):
           if str_equal(test_line[title_index], title):
               #title alone is insufficient, test author name too but remember that author string isn't always an exact match e.g. GabyA and Gaby A!
               # assume author won't write two stories with exact same name...
               if (test_line[author_index] != csv_line[author_index] and not
                       loose_equal(test_line[author_index], csv_line[author_index])):
                   continue     # loop and see if we find another matching title
               else:
                   archive_url = test_line[archive_url_index]
                   print('\t APPENDING to: {}'.format(archive_url))
                   break
                 
        assert archive_url
       
        # find the insertion file, going to hope they all have same basic format at end!
        # Note: because the local cache is searched first, multiple calls to append archive will magically work correctly!
        start_indx = archive_url.rfind("/")
        insertion_filename = archive_url[start_indx+1:]
        page_data = get_file(insertion_filename, False, archive_url)
        page_data = ensure_new_story_format(insertion_filename, page_data)


        if PRE_PRODUCTION:
            page_data = page_data.replace('/style/stories.css', '../templates/stories (for local use only).css')
            page_data = page_data.replace('/derby/back.gif', '../templates/back.gif')

        charset_info = page_data.find('<meta charset="utf-8">')
        if charset_info < 0:
            page_data = page_data.replace('<head>', '<head>\n <meta charset="utf-8"> \n')

        #search for and remove deprecated author addrs: <!--mailto: apterja@optusnet.com.au -->
        page_data = re.sub(r'<!--mailto:.{1,50} -->', '', page_data, re.I)

        #insert the jump links first:
        jump_link_string, jump_label = create_jump_lines(post_date, msg_id)

        assert JUMP_LINK_INSERTION_MARKER in page_data, "should have been tested"
        assert STORY_INSERTION_MARKER in page_data, "see above line"

        if jump_link_string in page_data and jump_label in page_data:
            print("    **** Append already performed (found jump link {})".format(jump_label))
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
                jump_label=jump_label,
                date=post_date,
                body=message_body)

            if JUMP_SECTION in page_data and (JUMP_SECTION + SEPERATOR_LINE) not in page_data:
                # To avoid double <hr> in new stories with no jump links we avoid adding the <hr>
                # till the first append, but only add it the 1st append.
                page_data = page_data.replace(JUMP_SECTION, JUMP_SECTION + SEPERATOR_LINE)

            # this is the place to modify white space between posts.
            new_page_data = (page_data
                .replace(JUMP_LINK_INSERTION_MARKER, jump_link_string +'\n' + JUMP_LINK_INSERTION_MARKER)
                .replace(STORY_INSERTION_MARKER, EMPTY_LINE + EMPTY_LINE + story_data + "\n" +  STORY_INSERTION_MARKER)
            )

            new_page_data = update_copyright(new_page_data, post_date)

            output_file = cached_path(insertion_filename)
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(new_page_data)

        if title not in csv_output:     # start with the archived story data from matching entry but only on first append
            #print('\tAdding title to csv output', title)
            csv_output[title] = test_line[:last_csv_input_index+1] + [insertion_filename]
            csv_output[title][action_index] = csv_line[action_index]
            csv_output[title][category_index] = csv_line[category_index]    # in case it get's recategorized?
        csv_output[title][post_date_index] = csv_line[post_date_index]      #update the dates on each subsequent append
        csv_output[title][final_post_index] = csv_line[final_post_index]
        if blurb:                              # suppose a new one could appear in a chapter
            csv_output[title][blurb_index] = blurb

        appendedArchive += 1
        continue

    elif action == "delete":
        #garbage post that is ignored here and deleted from forum
        print('\n*** Delete this post({}): "{}" by {}\n'.format(i+2, title, author))
        tbd_output.append(csv_line[:last_csv_input_index+1] + [''])
        #csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
        deleteCount += 1
        continue
    elif action == "dna":
        #Do Not Archive, so, duh, do nothing here, don't get removed from forum archive so could equally use no-op
        print('DNA this post({}): "{}" by {}'.format(i+2, title, author))
        extraneousActions+=1
        continue
    elif action == "no-op":
        #these are extraneous posts, for example, previously processed posts,
        # ignore here, but they will get archived from forum
        # (annoying!) print('No-op({}): "{}" by {}'.format(i+2, title, author))
        extraneousActions+=1
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
    with open(output_csv_filename, "w", newline='') as csv_file:
       writer = csv.writer(csv_file)
       writer.writerows(csv_output.values())

    if len(tbd_output) > 1:     #don't create unless there is something other than header in the file
        with open(output_tbd_filename, "w", newline='') as tbd_file:
            writer = csv.writer(tbd_file)
            writer.writerows(tbd_output)

except IOError:
    print("I/O error")


print(
'''Archive complete:
    {} story files created
    {} Amendments must be completed manually (refer to log or {})
    {} Forum Deletions to be completed manually
    {} Extraneous posts requiring no action
    {} New Stories (with {} Updates to those)
    {} Archived stories received ({} updates)'''.format(
    len(csv_output)-1, toAmend, output_tbd_filename, deleteCount, extraneousActions,
    archivedNew, appendedNew, len(csv_output)-1 -archivedNew, appendedArchive))
# len-1 deducts the header line, 

print("\nBe sure to scan back thru output for possible instructions or problems")
