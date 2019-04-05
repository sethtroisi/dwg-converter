# -*- coding: utf8 -*-
import csv
import os.path
import urllib.request
import re
import time

INPUT_CSV_PATH = "dwg-posts-2019-01-26.csv"
OUTPUT_CSV_PATH="dwg_index_update-2018_12_10_.csv"
ARCHIVE_TEMPLATE = "templates/story_archive_template.html"
CACHE_DIRECTORY = "cache/"
#Input CSV file should have the following columns with names specified in main below:
post_date_indx = 0
archive_date_indx = 1
msg_id_indx = 2
author_id_indx = 3
author_index = 4
title_index = 5
comment_index = 6
post_url_indx = 7
archive_url_indx = 8
final_post_indx=9


def create_filename(author, title, post_date):
    #use first 10 printable chars of author concatenated with first 10 of title + posting date
    #filename = add 10 of author
    author = re.sub('[^A-Za-z0-9]', '', author)
    title = re.sub('[^A-Za-z0-9]', '', title)
    post_date = re.sub('[^A-Za-z0-9]', '', post_date)
    filename = "cache/" + author[:9] + title[:9] + post_date + ".html"
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
    if not comment_string:
        post, comment_string = strip_comment(post, "Author's note")
    comment_string, blurb = strip_comment(comment_string, "Blurb")
    #TODO does author keyword case matter?
    #TODO insert the blurb into the index.

    #from dateutil.parser import parse
    #b = parse(post_date)
    #print(b.weekday())
    # SETH NOTE: b.strftime('%A') will give you the name (e.g. 'Wednesday')
    # SETH NOTE: b.strftime('%a') will give you abbreviated name (e.g. 'Wed')

    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        .replace("$SECTIONS", "")
        .replace("$BODY", post)
        .replace("$DATE", post_date)
        #TODO comment out this next line before generate last run.
        #TODO And either remove from template or send the template a "" for that param
        #TODO do something similar to insert jumps
        .replace("$OGLINK", '<a href="{}.html">originalpost</a><br>'.format(msg_id))
        .replace("$COPYRIGHT_YEAR", post_date[:4]))

    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    print("\t wrote {} to {}".format(
        len(new_story), output_name))


def get_file(cached_filename, url, chained):
    # this finds, caches, and opens a copy of a remote file

            # Check if we already downloaded & saved locally
            cache_name = CACHE_DIRECTORY + cached_filename
            print('Get/Create this url: "{}"'.format(url))

            if os.path.exists(cache_name):
                with open(cache_name, "r", encoding="utf-8") as cached:
                    page_data = cached.read()

            else:
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
                if chained:
                    #TODO implement the dechaining
                    pass
                print("Downloaded")
                time.sleep(2)
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
    print()

    # verify important column assumptions
    assert header[post_date_indx] == "last_update/Posting"
    assert header[msg_id_indx] == "Msg Id"
    assert header[author_index] == "author_name"
    assert header[title_index] == "title_name"
    assert header[comment_index] == "comments"
    assert header[post_url_indx] == "new posting - real url"
    assert header[archive_url_indx] == "archive real url"
    assert header[final_post_indx] == "FinalPost?"

    # While first entry of last line isn't a date
    while not ('200' in csv_input[-1][0] or '199' in csv_input[-1][0]):
        # remove the last line :)
        dropped = csv_input.pop()
        #print("Dropping:", ",".join(dropped))

    converted = 0
    for i, line in enumerate(csv_input):
        # Verify this line has correct number of columns
        if len(line) != len(header):
            print("Line is too long {}", len(line))

        action = line[comment_index]
        msg_id = line[msg_id_indx]

        # archived entries shouldn't have a action:
        if msg_id != "":
            assert action != "", (i+2, action)

        if action == "":
            continue

        post_date = line[post_date_indx]
        title = line[title_index]
        author = line[author_index]

        if action == "ArchiveNew" or action == "ArchiveNewFant":

            post_url = line[post_url_indx]
            page_data = get_file(msg_id+".html", str(post_url), False)
            print('ArchiveNew({}): "{}" from {}'.format(i+2, title, post_url))
            print("\t page len:", len(page_data))
            print("\t", page_data[0:40])

            # For now try the simpliest extraction possible
            # Assumes message starts with this string
            # and contains one internal "message-options" div
            post_start_text = '<div class="message-body">'
            post_end_text = '<div class="message-options">'
            post_start_index = page_data.index(post_start_text)
            post_end_index = page_data.index(post_end_text, post_start_index)
            print("\t source location: ", post_start_index, "to", post_end_index)
            assert post_start_index and post_end_index

           #TODO /div is a section marker. For jumps?
            message_body = page_data[post_start_index: post_end_index] + "</div>"

            print("\t", "{} characters copied, {:.1f}% of original html".format(
                len(message_body), 100 * len(message_body) / len(page_data)))
            print("\t", message_body[11:55], "...", message_body[-30:])

            format_new_post(msg_id, title, author, post_date, message_body)

            print()
            converted += 1
            #if converted >= 10:
                # Quit after converting a couple.
            #    break

            if action == "ArchiveNew":
                # TODO change metadata or save location.
                pass

            elif action == "ArchiveNewFant":
                #print("Archive New Fantasy: unimplemented")
                pass

        elif action == "Amend":
            post_url = line[post_url_indx]
            page_data = get_file(msg_id+".html", str(post_url), False)
            print('****** HUMAN intervention required to amend existing work:({}): "{}"  {}'.format(i+2, post_date, title))
            print("\t", page_data[0:40])

            #TODO Determine the correct associated archive file to fetch, this isn't correct csv line#
            #archive_url = line[archive_url_indx]
            # SETH NOTE if you have the Archive Title (as I see in the spreadsheet you can do this
            # archive_url = ""
            # for test_line in lines:
            #   if test_line[title_index] == line[archive_title_idx]:
            #       archive_url = test_line[archive_real_url_idx]
            #       break
            #
            # or this magic "list comprehension"
            #
            # archive_urls = [test_line[archive_real_url_idx] for test_line in lines
            #   if test_line[title_index] == line[archive_title_idx]]
            # assert len(archive_urls) == 1, archive_urls
            # archive_url = archive_urls[0]

            archive_url = "https://www.dwiggie.com//derby/abbiecb.htm"
            archive_page_data = get_file("Testfile", archive_url, True)
            print('\t local file to modify: "{}"'.format("Testfile"))
            #TODO mention filename in msg

            #TODO quit after once until we get it working.
            continue
        elif action == "no-op":
            #these are extraneous posts, get next post
            #print('No-op({}): "{}" by {}'.format(i+2, title, author))
            continue
        elif action == "delete":
            #garbage post that is ignored, get next post
            #print('Delete this post({}): "{}" by {}'.format(i+2, title, author))
            continue
        elif action == "dna":
            #Do Not Archive, so, duh, do nothing here! get next post
            #print('DNA this post({}): "{}" by {}'.format(i+2, title, author))
            continue
        elif action == "AppendArchive":
            #TODO need to fetch the old file, remove the stuff at end, and append the existing.
            #print('Append to Archived file: unimplemented')
            continue
        elif action == "AppendNew":
            #TODO Seth suggests writing the new stories out to the location and then running this algorithm doing same as AppendArchive
            #print('Append to new regenecy file: unimplemented')
            continue
        elif action == "AppendNewFant":
            #TODO this will probably be (nearly) same as AppendNew
            #print('Append to new Fantasy file: unimplemented')
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

print ("Converted:", converted)

