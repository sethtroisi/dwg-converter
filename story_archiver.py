# -*- coding: utf8 -*-
import csv
import os.path
import urllib.request
import re
import time

INPUT_CSV_PATH = "dwg-posts.csv"
OUTPUT_CSV_PATH="dwg_index_update-2018_12_10_.csv"
ARCHIVE_TEMPLATE = "templates/story_archive_template.html"
CACHE_DIRECTORY = "cache/"
STORY_SECTION_MARKER = "\n</div>"
STORY_INSERTION_MARKER = STORY_SECTION_MARKER + STORY_SECTION_MARKER
#Input CSV file should have the following columns with names specified in main below:
post_date_indx = 0
archive_date_indx = 1
msg_id_indx = 2
author_id_indx = 3
author_index = 4
title_index = 5
action_index = 6
category_index = 7
post_url_indx = 8
archive_url_indx = 9
final_post_indx=10
which_book_indx=11


def create_filename(author, title, post_date):
    #use first 10 printable chars of author concatenated with first 15 of title + posting date
    #filename = add 10 of author
    author = re.sub('[^A-Za-z0-9]', '', author)
    title = re.sub('[^A-Za-z0-9]', '', title)
    post_date = re.sub('[^A-Za-z0-9]', '', post_date)
    filename = "cache/" + author[:10] + title[:15] + post_date + ".html"
    return(filename)

def strip_comment(post, keyword):
    #finds and strips the keyword string up to either RA or the next line break
    # so multi line comments need to be delimited with RA.
    # returns the two seperated strings.

  br_tag = "<br />"
  start = post.find(keyword)
  end = post.find("RA", start)
  next_br = post.find(br_tag, max(start, end))
  post_dna = post[start: next_br + len(br_tag)]
  if post_dna:
    tempstring = post_dna
    print('\t removed: "{}"'.format(post_dna))
    return post.replace(post_dna, ""), tempstring
  return post, ""

def format_new_post(msg_id, title, author, post_date, post):
    # archive template is based on this sample file: https://www.dwiggie.com//derby/olde/coll1.htm
    # I removed <!-- mailto:lablanc@wctc.net --> after By $AUTHOR
    #
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

#TODO fix format of posting date?
#TODO insert the long line between appended sections which is, I think <hr><p>

    with open(ARCHIVE_TEMPLATE) as template_file:
        template = template_file.read()

    post, comment_string = strip_comment(post, "DNA")
    #TODO: why is this next conditional?? 
    if not comment_string:
        post, comment_string = strip_comment(post, "Author's note")
    comment_string, blurb = strip_comment(comment_string, "Blurb")
    #TODO does author keyword case matter?
    #TODO: if blurb appears, then that should be saved to output csv for index use
    
    #from dateutil.parser import parse
    #b = parse(post_date)
    #print(b.weekday())
    # SETH NOTE: b.strftime('%A') will give you the name (e.g. 'Wednesday')
    # SETH NOTE: b.strftime('%a') will give you abbreviated name (e.g. 'Wed')

    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        #todo: what is supposed to be in SECTIONS??
        .replace("$SECTIONS", "")
        .replace("$BODY", post + STORY_INSERTION_MARKER)
        .replace("$DATE", post_date)
        #TODO Seth had put this backlink in to jump to the original post but Margaret and I don't like that
        #.replace("$OGLINK", '<a href="{}.html">originalpost</a><br>'.format(msg_id))
        .replace("$OGLINK", "")
        .replace("$COPYRIGHT_YEAR", post_date[:4]))
 
    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    #TODO should we add something visible for unfinished stories?

    print("\t wrote {}  chars to {}".format(
        len(new_story), output_name))

    #TODO: need to create an array with the story details for updating the dwiggie index. 


def get_file(cached_filename, file_is_local, url = ''):
    # this finds, caches, and opens a copy of a file.
    # local asserts that we should find it in our cache because e.g. we just created it
    # note that my original copy of this file contains a recursive version of this to handle chaining.
    # i think seth now has implemented that elsewhere in seperate file. 

            # Check if we already downloaded & saved locally
            cache_name = CACHE_DIRECTORY + cached_filename
            #print('Get/Create this url: "{}"'.format(url))

            if os.path.exists(cache_name):
                with open(cache_name, "r", encoding="utf-8") as cached:
                    page_data = cached.read()

            else:
                #didn't find the file locally, should we have?
                assert not file_is_local, cache_name
                assert url.startswith("https:"), url

                #page_data = urllib.request.urlopen(url).read().decode("utf-8")
                request = urllib.request.urlopen(url)
                charset = request.info().get_content_charset("latin-1")
                page_data = request.read().decode(charset)
                page_data = page_data.replace(
                   '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
                   '')
                with open(cache_name, "w", encoding="utf-8") as cached:
                   cached.write(page_data)

                print("\t\tDownloaded")
                time.sleep(2)
            return page_data

def get_post_msg_body(csv_line):
#Fetch the body of the text from the post file:

    post_url = csv_line[post_url_indx]
    print('\t fetching post url: "{}"'.format(post_url))
    page_data = get_file(msg_id+".html", False, str(post_url))
    #print("\t page len:", len(page_data))
    #print("\t", page_data[0:40])

    # For now try the simpliest extraction possible from Phorum post file
    # Look for tags which bracket the story text. 
    # Assume template contains only of these tags

    post_start_text = '<div class="message-body">'
    post_end_text = '<div class="message-options">'
    post_start_text_index = page_data.index(post_start_text)
    post_end_text_index = page_data.index(post_end_text, post_start_text_index)
    #print("\t source location: ", post_start_text_index, "to", post_end_text_index)
    assert post_start_text_index and post_end_text_index
                 
    message_body = page_data[post_start_text_index: post_end_text_index]
    print("\t", "{} characters copied, {:.1f}% of original html".format(len(message_body), 100 * len(message_body) / len(page_data)))
    #print("\t", message_body[11:55], "...", message_body[-30:])


    return message_body

COPYRIGHT_PREFIX = '&copy; '
COPYRIGHT_POSTFIX = ' Copyright held by the author.'

def get_copyright(page_data):
    
    copyright_start_text_index = page_data.index(COPYRIGHT_PREFIX) + len(COPYRIGHT_PREFIX)
    copyright_end_text_index = page_data.index(COPYRIGHT_POSTFIX, copyright_start_text_index)
    assert copyright_start_text_index and copyright_end_text_index
    copyright = page_data[copyright_start_text_index: copyright_end_text_index]
    return(copyright);
            
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
    #print("Column Headers:")
    #print(", ".join(header))
    #print()

    # verify important column assumptions
    assert header[post_date_indx] == "last_update/Posting"
    assert header[msg_id_indx] == "Msg Id"
    assert header[author_index] == "author_name"
    assert header[title_index] == "title_name"
    assert header[action_index] == "action"
    assert header[category_index] == "category"
    assert header[post_url_indx] == "new posting - real url"
    assert header[archive_url_indx] == "archive real url"
    assert header[final_post_indx] == "FinalPost?"

    # Remove any extraneous entries at end of list (defined as ones that don't have good looking dates):
    while not ('200' in csv_input[-1][0] or '199' in csv_input[-1][0]):
        # remove the last line :)
        dropped = csv_input.pop()
        #print("Dropping:", ",".join(dropped))

    archivedNew = 0
    appendedNew = 0
    appendedArchive = 0
    for i, csv_line in enumerate(csv_input):
        # Verify this line has correct number of columns
        if len(csv_line) != len(header):
            print("csv_line is too long {}", len(csv_line))

        action = csv_line[action_index]
        category = csv_line[category_index]    #note that this value could be null
        msg_id = csv_line[msg_id_indx]

        # archived entries shouldn't have a action:
        if msg_id != "":
            assert action != "", (i+2, action)

        if action == "":
            continue

        post_date = csv_line[post_date_indx]
        author = csv_line[author_index]
        temp_title = csv_line[title_index]
        #title needs to be stripped of any excess verbiage, this is assuming that CSV has been groomed to insert '::' at end of simple title
        title_delimiter = '::'
        temp_index = temp_title.find(title_delimiter)
        if temp_index:
            title = temp_title[:temp_index]
        else:
            title = temp_title
        
        if action == "Amend":
            post_url = csv_line[post_url_indx]
            page_data = get_file(msg_id+".html", False, str(post_url))
            print('Amendment({}) - ***** HUMAN intervention required: "{}"  {}'.format(i+2, post_date, title))
           #TODO: is it helpful to fetch the relevant phorum file? have no way to know which archived file is being amended. 
           #TODO print('\t See this local file: "{}"'.format("Testfile")
            continue

        elif (action == "ArchiveNew"):

            if archivedNew >1:
                # TODO - skip after converting a couple, remove this when done
                continue

            print('ArchiveNew({}): "{}"'.format(i+2, title))
            message_body = get_post_msg_body(csv_line) 
            format_new_post(msg_id, title, author, post_date, message_body)

            archivedNew += 1
        
        elif action == "AppendNew":
            #TODO Seth suggests writing the new stories out to the location and then running this algorithm doing same as AppendArchive
            #In this case, we know the format of the file and thus are free to shove stuff into it.

            if appendedNew > 3:
                # TODO - skip after converting a couple, remove this when done
                continue

            print('AppendNew({}): {}'.format(i+2, title))
             
            #fetch post text to append to file created previously during this archive:
            message_body = get_post_msg_body(csv_line)

            #find the relevant file to append to which should now have an entry in the output CSV with a matching filename
            #TODO: , don't forget directory info... use this temp name for now:
            insertion_file = 'AmyANWLoveAcros20171214.html'     
            page_data = get_file(insertion_file, True)

            print('\t from {} into {}'.format(title, insertion_file))

            #find the insertion point:
            insertion_index =  page_data.rfind(STORY_INSERTION_MARKER)
            print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
            #print("\t", "{} characters copied, {:.1f}% of original html".format(len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index
            
            #TODO is .replace the correct thing to use?
            page_data = page_data.replace(STORY_INSERTION_MARKER, STORY_SECTION_MARKER + "<hr><p> Posted on " + post_date + message_body + STORY_INSERTION_MARKER)
            print(page_data[-200:len(page_data)])

            #update the copyright if necessary 
            text_copyright = get_copyright(page_data)
            new_copyright = post_date[:4]
            print("\t original copyright text: " + text_copyright + " new copyright " + new_copyright)
            #copyright is going to look like this: YYYY [ - YYYY] Copyright held by the author.
            match = text_copyright.find(new_copyright)
            if match == -1:      # our date is not yet in the string,  append new date, overwriting any prexisting second year:
                    updated_text_copyright = text_copyright[0:4] + " - " + new_copyright
                    page_data = page_data.replace(text_copyright, updated_text_copyright)
                    print("\n\n new copyright string: " + updated_text_copyright)    

            output_file = CACHE_DIRECTORY + insertion_file
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(page_data)

            appendedNew += 1
            continue
        
        elif action == "AppendArchive":
            #TODO need to determine file name, fetch the old file, remove the stuff at end, and append the existing.
            # look for same author, same filename, with earliest posting date - which should be the first match.
            if appendedArchive > 2:
                # TODO - skip after converting a couple, remove this when done
                continue

            #Determine the correct associated archive file to fetch - should be first CSV entry with matching title:
            #TODO do I need to worry about trailing spaces??
            archive_url = ''
            for j, test_line in enumerate(csv_input):
               if test_line[title_index].casefold() == title.casefold():
                   #TODO better verify that the author name is a least similar... and if not a match, at least print warning...
                   # could also compare indices and see if less than and close and posting dates work right. 
                   archive_url = test_line[archive_url_indx]
                   print('AppendArchive {} to {} from {}'.format(title, test_line[title_index], archive_url))
                   break
            if not archive_url:
                print('Appending({}): ***** ERROR: no archive file for {}'.format(i+2, csv_line[title_index]))
                continue
                
            # or this magic "list comprehension":
            # archive_urls = [test_line[archive_real_url_idx] for test_line in lines
            #   if test_line[title_index] == line[archive_title_idx]]
            # assert len(archive_urls) == 1, archive_urls
            # archive_url = archive_urls[0]

            #todo: whoops, need this to be written to so figure that out...
            archive_page_data = get_file(msg_id+".html", False, archive_url)
            print('\t local file to modify: "{}"'.format(msg_id+".html"))

            #TODO: now fetch the post file and suck out the data - share this with archive above
            # then open the archive file and shove the data into it ala'

            print('\tneed to finish Append Archive code...')
            
            appendedArchive += 1
            continue
 
        elif action == "no-op":
            #these are extraneous posts, get next post
            #TODO: return this statement for final run: print('No-op({}): "{}" by {}'.format(i+2, title, author))
            continue
        elif action == "delete":
            #garbage post that is ignored, get next post
            #print('Delete this post({}): "{}" by {}'.format(i+2, title, author))
            continue
        elif action == "dna":
            #Do Not Archive, so, duh, do nothing here! get next post
            #print('DNA this post({}): "{}" by {}'.format(i+2, title, author))
            continue
        else:
            print("unhandled action:", action)

        ##TODO Need to write out the index entry for any New and Append Action that happened.
            ## should we write the amend entry on assumption that it will happen??

        # SETH NOTE I don't fully understand the TODO BUT
        # try something like this
        # results_csv = list(csv.reader(results_csv_file))
        # results = {} # <- a "dictionary" with each "key" mapping to one (and only one) "value"
        # for line in results_csv:
        #   key = line[msg_id]
        #   results[key] = line
        #
        # # Now you can write
        # results[msg_id] = [NEW_CSV_DATA + ACTION]
        # # And that erases the old data
        # # Finally we save this by taking all the results e.g. the "values" in our dictionary
        # # And saving them to a new csv
        # with open(results_csv_file) as csv_file:
        #   writer = csv.writer(csv_file)
        #   for line in sorted(results.values()):
        #       writer.writerow(line)

