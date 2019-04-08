# -*- coding: utf8 -*-
import csv
import os.path
import urllib.request
import re
import time

INPUT_CSV_PATH = "dwg-posts.csv"
OUTPUT_CSV_PATH="dwg_archive_results.csv"
ARCHIVE_TEMPLATE = "templates/story_archive_template.html"
CACHE_DIRECTORY = "cache/"
STORY_SECTION_MARKER = "\n</div>"
STORY_INSERTION_MARKER = STORY_SECTION_MARKER + STORY_SECTION_MARKER
STORY_DIVISION_LINE = "<p><hr /></p>"
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


def create_filename(author, title, post_date):
    #use first 15 printable chars of author concatenated with first 15 of title + posting date
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
  resume_archive_tag = "RA"+br_tag         #TODO this isn't good, it finds RA in text, will there be a br_tag with it?? assume so...
  start = end = post.find(keyword)
  if start >= 0:
      end = post.find(resume_archive_tag, start)
  next_br = post.find(br_tag, max(start, end))
  post_dna = post[start: next_br]           # going to leave the white space inline because could have nested comments to strip
  if post_dna:
    tempstring = post_dna
    print('\t REMOVED: "{}"'.format(post_dna))
    return post.replace(post_dna, ""), tempstring
  return post, post_dna

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

    with open(ARCHIVE_TEMPLATE) as template_file:
        template = template_file.read()

    #look for blurb first so we don't lose it:
    #TODO does author keyword case matter? probably, better do this caseless? at least for Blurb
    post, blurb = strip_comment(post, "Blurb:")   #uh oh, blurb could be inside a DNA or not
    post, comment_string = strip_comment(post, "DNA:")
    post, comment_string = strip_comment(post, "Author's note")

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

    print("\t wrote {}  chars to {}".format(
        len(new_story), output_name))

    return output_name, blurb

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
                # Seems to work for forum posts.
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
#Fetch the body of the text from the post file:

    post_url = csv_line[post_url_index]
    print('\t fetching post url: "{}" => "{}"'.format(post_url, msg_id))
    page_data = get_file(msg_id+".html", False, str(post_url))
    #print("\t page len:", len(page_data))
    #print("\t", page_data[0:40])

    # For now try the simpliest extraction possible from Phorum post file
    # Look for tags which bracket the story text.
    # Assume template contains only of these tags

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

    return message_body

COPYRIGHT_PREFIX = '&copy; '        #code assumes these two prefixes are the same length so don't change!
OLD_COPYRIGHT_PREFIX = "&#169; "
COPYRIGHT_POSTFIX = ' Copyright held by the author.'

def get_copyright(page_data):
    copyright_start_text_index = page_data.find(COPYRIGHT_PREFIX)
    if copyright_start_text_index < 0:
        copyright_start_text_index = page_data.find(OLD_COPYRIGHT_PREFIX)
    copyright_end_text_index = page_data.find(COPYRIGHT_POSTFIX, copyright_start_text_index)
    assert copyright_start_text_index and copyright_end_text_index
    copyright = page_data[copyright_start_text_index: copyright_end_text_index]
    return copyright, copyright_start_text_index+ len(COPYRIGHT_PREFIX)

def update_copyright(page_data, post_date):
       #TODO: note that some old files have "date, date" not "date - date". Do any have date, date, date?
        text_copyright, copyright_index = get_copyright(page_data)
        new_copyright = post_date[:4]
        print("\t original copyright text: " + text_copyright + " new copyright " + new_copyright + " @ {}".format(copyright_index))
        #the newly inserted copyright is going to look like this: "c YYYY [ - YYYY] Copyright held by the author."
        match = text_copyright.find(new_copyright, copyright_index)
        if match == -1:      # our date is not yet in the string,  append new date, overwriting any prexisting second year:
                updated_text_copyright = COPYRIGHT_PREFIX + page_data[copyright_index:copyright_index+4] + " - " + new_copyright
                page_data = page_data.replace(text_copyright, updated_text_copyright)
                print("\t\t new copyright string: " + updated_text_copyright)
        return page_data

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
          #TODO do I have all of them in here?

    # Remove any extraneous entries at end of list (defined as ones that don't have good looking dates):
    while not ('200' in csv_input[-1][0] or '199' in csv_input[-1][0]):
        # remove the last line :)
        dropped = csv_input.pop()
        #print("Dropping:", ",".join(dropped))

    csv_output = {}
    csv_output["header"] = header + ["New Filename"]

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
            #Note: have no way to know which file (archived or new) is being amended, so let human fetch both the post and archived text
            #or could groom the csv to include the correct info...
            print('Amendment({}) - ***** HUMAN INTERVENTION required: "{}"  {} modify file and update CSV'.format(i+2, post_date, title))
            #TODO print('\t See this local file: "{}"'.format("Testfile")

            #Save all the data about this story because human be making a change to it:
            assert title not in csv_output      #TODO this may not be a safe assumption
            csv_output[title] = csv_line[:last_csv_input_index+1] + [""]     #TODO - we don't have a file to modify, human will have to add it.
            csv_output[title][title_index] = title
            csv_output[title][post_date_index] = csv_line[post_date_index]
            csv_output[title][final_post_index] = csv_line[final_post_index]

            continue

        elif (action == "ArchiveNew"):

            if archivedNew >=2:
                # TODO - skip after converting a couple, remove this when done
                continue

            print('ArchiveNew({}): "{}"'.format(i+2, title))
            message_body = get_post_msg_body(csv_line)
            new_filename, blurb = format_new_post(msg_id, title, author, post_date, message_body)

            #Save all the (new) data about this story (use stripped title) and the file (stripped of it's path name) where the new story resides:
            assert title not in csv_output
            csv_line[blurb_index] = "tbd"
            csv_output[title] = csv_line[:last_csv_input_index+1] + [new_filename[len(CACHE_DIRECTORY):]]
            csv_output[title][title_index] = title
            csv_output[title][creation_date_index] = csv_line[post_date_index]
            if blurb:
                csv_output[title][blurb_index] = blurb
            #print(csv_output[title])

            archivedNew += 1

        elif action == "AppendNew":
            #TODO Seth suggests writing the new stories out to the location and then running this algorithm doing same as AppendArchive
            #In this case, we know the format of the file and thus are free to shove stuff into it without care.

            if appendedNew >= 1:
                # TODO - skip after converting a couple, remove this when done
                continue

            print('AppendNew({}): {}'.format(i+2, title))

            #fetch post text to append to file created previously during this archive:
            message_body = get_post_msg_body(csv_line)

            #find the relevant file to append to which should now have an entry in the output CSV from previous post
            assert title in csv_output, "Appending to non-existent story!"
            insertion_file = csv_output[title][to_archive_filename_index]
            page_data = get_file(insertion_file, True)

            print('\t from {} into {}'.format(title, insertion_file))

            #find the insertion point:
            insertion_index =  page_data.rfind(STORY_INSERTION_MARKER)
            print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
            print("\t", "{} characters copied, {:.1f}% of new file".format(len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index

            #TODO is .replace the correct thing to use?
            page_data = page_data.replace(STORY_INSERTION_MARKER, STORY_SECTION_MARKER + "<hr><p> Posted on " + post_date + message_body + STORY_INSERTION_MARKER)

            page_data = update_copyright(page_data, post_date)

            #TODO - need to strip any "to be continued" and if final, ensure that there is "the end" or "fin" or some such.

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

            if appendedArchive >= 4:
                # TODO - skip after converting a couple, remove this when done
                continue

            print('AppendArchive({}): {}'.format(i+2, title))

            #fetch post text to append to archived file:
            message_body = get_post_msg_body(csv_line)

            #Determine the correct associated archive file to fetch - should be first CSV entry with matching title:
            #TODO do I need to worry about trailing spaces??
            archive_url = ''
            for j, test_line in enumerate(csv_input):
               if test_line[title_index].casefold() == title.casefold():
                   #title alone is insufficient, test author name too but remember that author string isn't always exact match!
                   if (test_line[author_index] != csv_line[author_index] and
                      test_line[author_index] not in csv_line[author_index] and
                      csv_line[author_index] not in test_line[author_index]):
                       print("\tWARNING: appending with non-matching author names: {} {}):".format(csv_line[author_index], test_line[author_index]))
                   archive_url = test_line[archive_url_index]
                   print('\tAppending to: {}'.format(archive_url))
                   break
            assert archive_url
            #print('Appending({}): ***** ERROR: no archive file for {}'.format(i+2, csv_line[title_index]))

            # find the insertion file, going to hope they all have same basic format at end!
            # Note: because the local cached is searched first, multiple calls to append archive will magically work correctly!
            start_indx = archive_url.rfind("/")
            insertion_filename = archive_url[start_indx:]
            page_data = get_file(insertion_filename, False, archive_url)

            insertion_index =  page_data.rfind(STORY_DIVISION_LINE)
            print("\t insert location: {} in {} length file".format(insertion_index, len(page_data)))
            print("\t", "{} characters copied, {:.1f}% of new file".format(len(message_body), 100 * len(message_body) / len(page_data)))
            assert insertion_index

            #TODO set up the jump link:
            jump_label = '\n<a name="new' + csv_line[post_date_index] + '">'
            jump_string = '\n<a href="#new'+csv_line[post_date_index]+'">Jump to new as of ' + csv_line[post_date_index] + '</a><br />'
            jump_link_index = page_data.rfind('>Jump to new as of')
            if jump_link_index < 0:
                print("\nJump link" +page_data[jump_link_index:20])
                jump_link_index = page_data.rfind("\n")+1
                print("\nJump link" + page_data[jump_link_index:20])
            else:
                jump_link_index = page_data.find(STORY_DIVISION_LINE)
                assert jump_link_index, "Malformed story"
                jump_link_index = jump_link_index + len(STORY_DIVISION_LINE)
                jump_string = jump_string + STORY_DIVISION_LINE

            #TODO, is this best way to  copy the content?
            assert jump_link_index < insertion_index
            new_page_data = page_data[:jump_link_index] + jump_string + page_data[jump_link_index:insertion_index] + "\n" + STORY_DIVISION_LINE + \
                            '\n' + jump_label + "\n<hr><p> Posted on " + post_date + "\n" + message_body + page_data[insertion_index:]

            # Note that we're not putting our new end marker in old format stories, will wait an do all old files at once.

            new_page_data = update_copyright(new_page_data, post_date)

            #TODO - need to strip any "to be continued" and if final, ensure that there is "the end" or "fin" or some such.

            output_file = CACHE_DIRECTORY + insertion_filename
            with open(output_file, "w", encoding="utf-8") as output_file:
                output_file.write(new_page_data)

            #TODO: story any necessary story data in the output CSV, might or might not already have an entry.
            if title not in csv_output:     # start with the archived story data
                csv_output[title] = test_line[:last_csv_input_index+1] + [new_filename[len(CACHE_DIRECTORY):]]
                csv_output[title][action_index] = csv_line[action_index]
                csv_output[title][category_index] = csv_line[category_index]
            csv_output[title][post_date_index] = csv_line[post_date_index]
            csv_output[title][final_post_index] = csv_line[final_post_index]

            #Save all the (new) data about this story (use stripped title) and the file (stripped of it's path name) where the new story residescsv_line[blurb_index] = "tbd"
            print(csv_output[title])

            appendedArchive += 1
            continue

        elif action == "no-op":
            #these are extraneous posts, get next post55
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

    try:
        with open(OUTPUT_CSV_PATH, "w", newline='') as csv_file:
           # this one just did the keys:
           #writer = csv.writer(csv_file)
           #writer.writerows(csv_output)
           # this one doesn't format csv correctly: includes the [] and "
           #for key in csv_output.keys():
               #csv_file.write("%s\n"% (csv_output[key]))
            # this does the keys and then gets an error
            #csv_columns = header + ["New Filename"]
            #writer = csv.DictWriter(csv_file, fieldnames=csv_columns)
            #writer = csv.DictWriter(csv_file, csv_output.keys())
            #writer.writeheader()
            #for data in csv_output:
            #    writer.writerow(data)

            # this one works but writes an empty row between each, why?
            writer = csv.writer(csv_file)
            for key, value in csv_output.items():
                writer.writerow(value)

    except IOError:
        print("I/O error")

    csv_file.close()
