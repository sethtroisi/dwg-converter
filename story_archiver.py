# -*- coding: utf8 -*-
import csv
import os.path
import urllib.request
import datetime
import re
import subprocess
import time
import tempfile

#-----------------------

INPUT_CSV_PATH = "dwg-posts.csv"
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
JUMP_TEMPLATE = '''
<span class="navigation-links">
    {{jump_link}}
    {}
</span>'''.format(JUMP_LINK_INSERTION_MARKER)

# For POST_BODY_SECTION
STORY_TEMPLATE = '''
<div class="post">
  <hr><p>
  {jump_label}<i>Posted on {date}</i><br><br>
  {body}
</div>
'''

# For CLOSING_SECTION
STORY_STATUS_MARKER = '<span id="story-insertion-marker closing-status">'
STORY_STATUS_MARKER_CLOSE = '</span>'
# We don't need a 2nd marker but a better description is nice
STORY_INSERTION_MARKER = STORY_STATUS_MARKER

# From STORY_STATUS_MARKER to end of file (closing section + ToBeContinued + copyright + boilerplate html)
FINAL_SECTION_LENGTH_MAX = 220 # ToBeContinued is like really long man.

#-----------------------

BR_TAG = "<br />"
ITALIC_TAG = "<i>"
ITALIC_END_TAG = "</i>"
BOLD_TAG = "<b>"
BOLD_END_TAG = "</b>"

SEPERATOR_LINE = "<p><hr><p>"        # this draws visual horizontal lines. 

#-----------------------


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
    filename = "cache/" + author[:10] + title[:15] + post_date + ".html"
    return(filename)

def find_keyword_string (post, keyword, caseless = False ):   
    # finds and returns the string following keyword up to next BR_TAG
    # will remove any leading white space and embedded html tags

  if caseless:
      start = post.lower().find(keyword.lower())
  else:
      start = post.find(keyword)      
  if start >= 0:    # found our tag;
      end = post.find(BR_TAG, start)
      keyword_string = post[start+len(keyword): end]
  else:
      keyword_string = ''
  
  if keyword_string:
    #TODO remove html tags, <b> <i> </b> </i> are most likely but should probably do a more general replace of anything in <>?
    keyword_string = keyword_string.replace(ITALIC_TAG,'')
    keyword_string = keyword_string.replace(ITALIC_END_TAG,'')
    keyword_string = keyword_string.replace(BOLD_TAG,'')
    keyword_string = keyword_string.replace(BOLD_END_TAG,'')
    keyword_string = keyword_string.strip();
    #continue
  return keyword_string

def strip_comment(post, keyword, caseless = False ):   
    # finds and strips the keyword and associated text post but not the following white space
    # (need to leave that else serial strips might fail)
    # returns the two seperated strings.
    # TODO: well, need to worry about case, and optional ": " and any formatting pairs that we truncate...
    # POST files use "<br />" for single lines and RA as multiline delimiters
    # TODO archive files use other things - \n or <p>??
    # so multi line comments need to be delimited with RA. and should be searched for after others to avoid losing info
    
    #TODO: need to revisit comment stripping, I think this needs to go to next BR.
    #TODO: this has a problem with text formatting...

  resume_archive_tag = "RA"+BR_TAG         #TODO this isn't good, it finds RA in text, will there be a BR_TAG with it?? assume so...

  if caseless:
      start = end = post.lower().find(keyword.lower())
  else:
      start = end = post.find(keyword)
  if start >= 0:    # found our tag;
      end = post.find(resume_archive_tag, start)
  next_br = post.find(BR_TAG, max(start, end))
  post_dna = post[start: next_br]           # going to leave the trailing white space inline because could have nested comments to strip
  if post_dna:  
    tempstring = post_dna
    print('\t REMOVED: "{}"'.format(post_dna))
    return post.replace(post_dna, ""), tempstring
  return post, post_dna

def get_blurb(post):
    
    blurb = find_keyword_string(post, "Blurb:", True)
    if not blurb:
        blurb = find_keyword_string(post, "Blurb", True)
    if not blurb:
        blurb = find_keyword_string(post, "Summary:", True)
    if not blurb: 
        blurb = find_keyword_string(post, "Summary", True)  # this could match something in the text but since we're not stripping it here, will go with it
    if blurb:
        print('\t Blurb: ' + blurb)
    return blurb

def format_new_post(msg_id, title, author, post_date, post):
    # archive template is based on this sample file: https://www.dwiggie.com//derby/olde/coll1.htm
    # TITLE, AUTHOR, COPYRIGHT_YEAR
    #
    # SECTIONS came from
    #   <hr><p>
    #   <a href="https://www.dwiggie.com//derby/olde/coll1.htm#new22">Jump to new as of July 22, 1999</a><br>
    #   <a href="https://www.dwiggie.com//derby/olde/coll1.htm#new5">Jump to new as of August 5, 1999</a>
    #   </p><hr><p>
    #
    # Chapter titles are notated like this
    #   <font size="+1" color="#336666"> NAME </font> </p><p>
    # Followed often by
    #   <i> Posted on  Wednesday, 14 July 1999</i></p><p>
    #sections_header = '<hr><p>'
    #sections_line = '<a href="#{}">{}</a><br>'
    #sections_footer = '</p><hr><p>'
    #section_link = '<a name="{}"></a>'


    with open(ARCHIVE_TEMPLATE) as template_file:
        template = template_file.read()
 
    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        .replace("$BODY", post + "\n" + STORY_INSERTION_MARKER)
        .replace("$DATE", post_date)
        #NOTE Seth had put this backlink in to jump to the original post but Margaret and I don't like that
        #.replace("$OGLINK", '<a href="{}.html">originalpost</a><br>'.format(msg_id))
        .replace("$COPYRIGHT_YEAR", post_date[:4]))
 
    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    print("\t wrote {}  chars to {}".format(
        len(new_story), output_name))

    return output_name

def get_file(cached_filename, file_is_local, url = ''):
    # this finds, caches, and opens a copy of a file.
    # file_is_local asserts that we should find it in our cache because e.g. we just created it
    # note that my original copy of this file contains a recursive version of this to handle chaining.
    # i think seth now has implemented that elsewhere in seperate file. 

            # Check if we already downloaded & saved locally
            cached_name = CACHE_DIRECTORY + cached_filename
            #print('Get/Create this url: "{}"'.format(url))

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
                page_data = page_data.replace(
                   '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
                   '')
                with open(cached_name, "w", encoding="utf-8") as cached:
                   cached.write(page_data)

                print("\t\tDownloaded")
                time.sleep(2)
            return page_data

def get_post_msg_body(csv_line):
# Fetch the body of the text from the post file
# THe extranouse author notes will be stripped in here and
# any blurb will be returned

    post_url = csv_line[post_url_index]
    print('\t fetching post url: "{}"'.format(post_url))
    page_data = get_file(msg_id+".html", False, str(post_url))
    #print("\t page len:", len(page_data))
    #print("\t", page_data[0:40])

    # For now try the simpliest extraction possible from Phorum post file
    # Look for tags which bracket the story text and Assume template contains only one of these tags!

    post_start_text = '<div class="message-body">'
    post_end_text = '<div class="message-options">'
    post_start_text_index = page_data.index(post_start_text)
    post_start_text_index=post_start_text_index+len(post_start_text)
    post_end_text_index = page_data.index(post_end_text, post_start_text_index)
    #print("\t source location: ", post_start_text_index, "to", post_end_text_index)
    assert post_start_text_index and post_end_text_index
                 
    message_body = page_data[post_start_text_index: post_end_text_index]
    print("\t", "{} characters copied, {:.1f}% of original html".format(len(message_body), 100 * len(message_body) / len(page_data)))
    #print("\t", message_body[11:55], "...", message_body[-30:])

    blurb = get_blurb(message_body)    
    post, comment_string = strip_comment(message_body, "DNA:")
    post, comment_string = strip_comment(message_body, "Author's note", True) #TODO or at least with and without cap N. need to do this caseless?
                                #found one multiline note with "End Authors note"
    post, comment_string = strip_comment(message_body, "A/N")
    # prune any leading BR_TAGs left at head of body after comment stripping.
    post = post.strip()
    while post[0:len(BR_TAG)] == BR_TAG:
        post = post[len(BR_TAG):]
    #TODO remove from end too so that control the spacing
   
    return message_body, blurb

COPYRIGHT_PREFIX = '&copy; '        #code assumes these two prefixes are the same length so don't change!
OLD_COPYRIGHT_PREFIX = "&#169; "
ANOTHER_COPYRIGHT_PREFIX = '©'
COPYRIGHT_POSTFIX = ' Copyright held by the author.'

def get_copyright(page_data):
    copyright_start_text_index = page_data.find(COPYRIGHT_PREFIX)
    if copyright_start_text_index < 0:
        copyright_start_text_index = page_data.find(OLD_COPYRIGHT_PREFIX)
        if copyright_start_text_index < 0:
            copyright_start_text_index = page_data.find(ANOTHER_COPYRIGHT_PREFIX)
            
    assert copyright_start_text_index > 0, "source missing copyright statement"
    copyright_end_text_index = page_data.find(COPYRIGHT_POSTFIX, copyright_start_text_index)
    assert copyright_start_text_index and copyright_end_text_index
    copyright_text = page_data[copyright_start_text_index: copyright_end_text_index]
    return copyright_text, copyright_start_text_index + len(COPYRIGHT_PREFIX)

def update_copyright(page_data, post_date):
        text_copyright, copyright_index = get_copyright(page_data)
        new_copyright_year = post_date[:4]
        #print("\t original copyright text: " + text_copyright + " new copyright " + new_copyright_year + " @loc {}".format(copyright_index))
        #the newly inserted copyright is going to look like this: "c YYYY [ - YYYY] Copyright held by the author."
        match = text_copyright.find(new_copyright_year)
        if match == -1:      # our date is not yet in the string,  append new date, overwriting any prexisting second year:
                updated_text_copyright = COPYRIGHT_PREFIX + page_data[copyright_index:copyright_index+4] + " - " + new_copyright_year
                page_data = page_data.replace(text_copyright, updated_text_copyright)
                print("\t\t new copyright string: " + updated_text_copyright)
        return page_data

def html_cleanup(page_data):
    # Safe, easy to apply HTML cleanups.

    # fixing <hr /> with or without spaces
    (page_data, fixed_hrs) = re.subn(r"<hr[\s/]+>", "<hr>", page_data)
    if fixed_hrs > 0:
        print("\tFixed {} HRs".format(fixed_hrs))

    # fix <p><hr></p> which is invalid because hr is a block level
    (page_data, fixed_end_p) = re.subn(r"(<p><hr[^>]*>)</p>", r"\1<p>", page_data)
    if fixed_end_p > 0:
        print("\tFixed {} <p><hr></p>".format(fixed_end_p))

    # TODO try out removing all </p> and see if visually different (will help out with some problems around <i>/<b>)

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
    
    final_lines =  page_data[story_status_index:].split("\n")
    # All non-empty lines near the end of the file
    final_lines = [line.strip().lower() for line in final_lines if len(line.strip()) > 0]
    if not final_lines[0].startswith(STORY_STATUS_MARKER):
        assert ignore_assert, ("First line doesn't start with <span...story-insertion-marker closing-status...", final_lines)
        return False
    if not final_lines[1] == SEPERATOR_LINE:
        assert ignore_assert, ("Second line was not " + SEPERATOR_LINE, final_lines)
        return False
    if not final_lines[2].startswith((COPYRIGHT_PREFIX, OLD_COPYRIGHT_PREFIX, ANOTHER_COPYRIGHT_PREFIX)):
        assert ignore_assert, ("Third line didn't start with any known copyright symbol", final_lines)
        return False
    return True


def ensure_new_story_format(page_data):
    if story_in_new_format(page_data):
        return page_data

    # Human is responsible for
    #   1. Moving the JUMP_LINK_INSERTION_MARKER to the right point (after others or after navigations or after author name)
    #       a. If no navigate / jump section add a SEPERATOR_LINE (<p><hr></p>
    #   2. Moving STORY_STATUS_MARKER
    #   3. Verifying STORY_STATUS_MARKER, SEPERATOR_LINE, &copy all in a row near the end

    page_data = html_cleanup(page_data)

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
    subprocess.check_output(["notepad.exe", temp_file_path])

    with open(temp_file_path, encoding="utf-8") as f:
        new_data = f.read()

    # TODO more verification that files are mostly the same
    # if 1a then <p><hr></p> adds ~15 characters
    assert len(write_data) + 20 >= len(new_data) > len(page_data), (len(write_data), len(new_data), len(page_data))

    os.unlink(temp_file_path)

    assert not new_data.startswith(JUMP_LINK_INSERTION_MARKER), "You forgot to move the jump marker!"
    assert not new_data.endswith(STORY_STATUS_MARKER_CLOSE), "You forgot to move the stuff at the bottom"
    assert story_in_new_format(new_data, ignore_assert=False)

    return new_data

    
def strip_to_be_continued(page_data):
    #TODO: this needs to look for and remove any "to be continued" variants at the end of the section

    #tbd
    return page_data

def ensure_has_end(message_body):
    #TODO: look at end of message body and ensure that it has some text either The End or FIN (caseless search)
    return message_body


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

    # verify important column assumptions
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

    toAmend = 0
    archivedNew = 0
    appendedNew = 0
    appendedArchive = 0
    for i, csv_line in enumerate(csv_input):
        # Verify this line has correct number of columns
        if len(csv_line) != len(header):
            print("csv_line is too long {}", len(csv_line))

        action = csv_line[action_index]
        category = csv_line[category_index]    #note that this value could be null
        msg_id = csv_line[msg_id_index]

        # archived entries shouldn't have a action:
        if msg_id != "":
            assert action != "", (i+2, action)

        if action == "":
            continue

        post_date = csv_line[post_date_index]
        author = csv_line[author_index]
        temp_title = csv_line[title_index]
        #title needs to be stripped of any excess verbiage, this assumes that CSV has been groomed to insert '::' at end of simple title
        title_delimiter = '::'
        temp_index = temp_title.find(title_delimiter)    # returns -1 if not found
        if temp_index > 0:
            title = temp_title[:temp_index]
        else:
            title = temp_title
        
        if action == "Amend":
            post_url = csv_line[post_url_index]
            page_data = get_file(msg_id+".html", False, str(post_url))
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

        elif (action == "ArchiveNew"):

            #if archivedNew >=2:    # TODO - skip after converting a couple, remove this when done
            #    continue

            print('ArchiveNew({}): "{}"'.format(i+2, title))
            message_body, blurb = get_post_msg_body(csv_line) 
            new_filename = format_new_post(msg_id, title, author, post_date, message_body)

            #Save all the (new) data about this story (use stripped title) and the file (stripped of it's path name) where the new story resides:
            assert title not in csv_output
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

            #if appendedNew >= 1:     #TODO - skip after converting a couple, remove this when done
            #    continue

            print('AppendNew({}): {}'.format(i+2, title))
             
            #fetch post text to append to file created previously during this archive:
            message_body, blurb = get_post_msg_body(csv_line)
            if blurb:
                if csv_line[blurb_index]:
                    print("\tFOUND NEW BLURB: ")
                csv_line[blurb_index] = blurb

            #find the relevant file to append to which should now have an entry in the output CSV from previous post
            if not title in csv_output: # see if it is there caseless and if so, correct current titles to match saved title
                matches = [csv_output[key] for key in csv_output if key.lower() == title.lower()]
                assert len(matches) == 1, (title, matches)
                title = csv_line[title_index] = matches[0][title_index]
                # if not title.casefold() in (name.casefold() for name in csv_output):     
            assert title, "Appending to non-existent story!"
            insertion_file = csv_output[title][to_archive_filename_index]
            page_data = get_file(insertion_file, True) 
            
            print('\t from {} into {}'.format(title, insertion_file))

            #find the insertion point:
            insertion_index =  page_data.rfind(STORY_INSERTION_MARKER)
            print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
            print("\t", "{} characters copied, {:.1f}% of new file".format(len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index

            #Deal with To Be Continued and The End
            page_data = strip_to_be_continued(page_data)
            if csv_line[final_post_index]:
                message_body = ensure_has_end(message_body)
            
            story_data = STORY_TEMPLATE.format(jump_label='', date=post_date, body=message_body,)
            page_data = page_data.replace(STORY_INSERTION_MARKER,
                                          story_data + "\n" + STORY_INSERTION_MARKER)
            
            page_data = update_copyright(page_data, post_date)

            
            output_file = CACHE_DIRECTORY + insertion_file
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(page_data)

            #update any necessary story data
            csv_output[title][post_date_index] = csv_line[post_date_index]
            csv_output[title][final_post_index] = csv_line[final_post_index]
            #print(csv_output[title])

            appendedNew += 1
            continue
        
        elif action == "AppendArchive":

            #if appendedArchive >= 50:    # TODO - skip after converting a couple, remove this when done
            #    continue

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
            insertion_filename = archive_url[start_indx:]
            page_data = get_file(insertion_filename, False, archive_url)
            page_data = ensure_new_story_format(page_data)

            #TODO: this is temp code to make styles look correct in local work, remove before done:
            page_data = page_data.replace('/style/stories.css', 'style/stories.css')
            page_data = page_data.replace('/derby/back.gif', 'derby/back.gif')

            charset_info = page_data.find('<meta charset="utf-8">')
            if charset_info < 0:
                page_data = page_data.replace('<head>', '<head>\n <meta charset="utf-8"> \n')

            #search for and remove deprecated author addrs: <!--mailto: apterja@optusnet.com.au -->
            start_index = page_data.find('<!--mailto:')
            if start_index >=0:
                end_index = page_data.find('-->', start_index)
                author_str = page_data[start_index:end_index+3]
                print('\t REMOVED: ' + author_str)
                page_data = page_data.replace(author_str, '')
                
            #insert the jump links first: 
            jump_string_date = datetime.datetime.strptime(post_date, "%Y-%m-%d")
            jump_string_date_str = jump_string_date.strftime('%A %B %d, %Y')
            jump_string = '\n<a href="#new{}">Jump to new as of {}</a><br />'.format(
                csv_line[post_date_index], jump_string_date_str)

            jump_label = '<a id="new{}"></a>'.format(post_date)

            assert JUMP_LINK_INSERTION_MARKER in page_data, "should have been tested"
            assert STORY_INSERTION_MARKER in page_data, "see above line"

            #Deal with To Be Continued vs The End:
            page_data = strip_to_be_continued(page_data)
            if csv_line[final_post_index]:
                message_body = ensure_has_end(message_body)

            insertion_index =  page_data.index(STORY_INSERTION_MARKER)           
            print("\t insert location: {} in {} length file ({} from end)".format(
                insertion_index, len(page_data), insertion_index - len(page_data)))
            print("\t {} characters copied, {:.1f}% of new file".format(
                len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index and insertion_index > (len(page_data)- FINAL_SECTION_LENGTH_MAX)

            story_data = STORY_TEMPLATE.format(
                jump_label=jump_label + "\n",
                date=post_date,
                body=message_body)

            new_page_data = (page_data
                .replace(JUMP_LINK_INSERTION_MARKER, jump_string + "\n" + JUMP_LINK_INSERTION_MARKER)
                .replace(STORY_INSERTION_MARKER, story_data + "\n" +  STORY_INSERTION_MARKER)
            )
            
            new_page_data = update_copyright(new_page_data, post_date)
            
            output_file = CACHE_DIRECTORY + insertion_filename
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(new_page_data)

            if title not in csv_output:     # start with the archived story data
                csv_output[title] = test_line[:last_csv_input_index+1] + [insertion_filename]
                csv_output[title][action_index] = csv_line[action_index]
                csv_output[title][category_index] = csv_line[category_index]
            csv_output[title][post_date_index] = csv_line[post_date_index]
            csv_output[title][final_post_index] = csv_line[final_post_index]  
            
            appendedArchive += 1
            continue
 
        elif action == "no-op":
            #these are extraneous posts, ignore here, let them archive in forum
            #TODO: return this statement for final run: print('No-op({}): "{}" by {}'.format(i+2, title, author))
            #csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
            continue
        elif action == "delete":
            #garbage post that is ignored here and deleted from forum
            #print('Delete this post({}): "{}" by {}'.format(i+2, title, author))
            #csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
            continue
        elif action == "dna":
            #Do Not Archive, so, duh, do nothing here, do they get removed from forum archive? 
            #print('DNA this post({}): "{}" by {}'.format(i+2, title, author))
            #csv_output[title] = csv_line[:last_csv_input_index+1] + ['']
            continue
        else:
            print("unhandled action:", action)

    try:
        with open(OUTPUT_CSV_PATH, "w", newline='') as csv_file:
           writer = csv.writer(csv_file)
           writer.writerows(csv_output.values())
           
        with open(OUTPUT_CSV_PATH + '.tbd', "w", newline='') as tbd_file:
           writer = csv.writer(tbd_file)
           writer.writerows(tbd_output)

                
    except IOError:
        print("I/O error") 

    print('Archive complete: \n\t{} story files created\n\t\ \
                {} Amendments must be completed manually (see log or CSV file)\n\t \
                {} New Stories (with {} Updates to those)\n\t \
                {} Archive Updates ({} stories)'.format(len(csv_output)-1, toAmend, archivedNew, appendedNew, \
                                                         appendedArchive, (len(csv_output)-1-archivedNew)))                                              

    csv_file.close()
       
