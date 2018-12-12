import csv
import os.path
import urllib.request
import re
import time

INPUT_CSV_PATH = "2018-12-10-dwg-posts.csv"
OUTPUT_CSV_PATH="2018_12_10_dwg_index_update.csv"
ARCHIVE_TEMPLATE = "story_archive_template.html"

def create_filename(author, title, post_date):
    #use first 10 printable chars of author concatenated with first 10 of title + posting date
    #filename = add 10 of author
    author = re.sub('[^A-Za-z0-9]', '', author)
    title = re.sub('[^A-Za-z0-9]', '', title)
    post_date = re.sub('[^A-Za-z0-9]', '', post_date)
    filename = "cache/" + author[:9] + title[:9] + post_date + ".html"
    return(filename)

def strip_comments(message):
    #this needs to search for "dna" followed by text and either RA or <br /><br /> or??
    #people don't follow any specific convention, it looks like...
    #will it always be at beginning? or possibly in middle?, better check
    #can there be more than one?? better look
    #dna_loc = ??
    #resume_loc = ??
    #checks
    #return truncated message

    return(message)

def stripDNA(post):
  br_tag = "<br />"
  start = post.find("DNA")
  end = post.find("RA", start)
  next_br = post.find(br_tag, max(start, end))
  post_dna = post[start: next_br + len(br_tag)]
  if post_dna:
    print ('\t found: "{}"'.format(post_dna))
    return post.replace(post_dna, "")
  return post

def format_new_post(msg_id, title, author, post_date, post):
    # archive template is:
    # A modified https://www.dwiggie.com//derby/olde/coll1.htm
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
    # TODO consider adding link to original post

    with open(ARCHIVE_TEMPLATE) as template_file:
        template = template_file.read()

    post = stripDNA(post)
    new_story = (template
        .replace("$TITLE", title)
        .replace("$AUTHOR", author)
        .replace("$SECTIONS", "")
        .replace("$BODY", post)
        #TODO comment out this next line before generate last run.
        #TODO And either remove from template or send the template a "" for that param
        .replace("$OGLINK", '<a href="{}.html">originalpost</a><br>'.format(msg_id))
        .replace("$COPYRIGHT_YEAR", post_date[-4:]))

    output_name = create_filename(author, title, post_date)

    with open(output_name, "w", encoding="utf-8") as output_file:
        output_file.write(new_story)

    print("\t wrote {} to {}".format(
        len(new_story), output_name))


########## MAIN ##############

if not os.path.exists("cache"):
        os.makedirs("cache")

with open(INPUT_CSV_PATH, encoding='utf-8') as csv_file:
    csv_reader = csv.reader(csv_file)
    lines = list(csv_reader)

    print("Archiving Dwiggie posts from: ", INPUT_CSV_PATH);
    print("Number of rows: {}, number of columns: {}".format(
        len(lines), len(lines[0])))
    print()

    header = lines.pop(0)

    # Join each item in the list with ', ' and print
    print("Column Headers:")
    print(", ".join(header))
    print()

    # We are going to need to look up new url a lot
    post_index = 0
    assert header[post_index] == "last_update/Posting"
    msg_index = 2
    assert header[msg_index] == "Msg Id"
    author_index = 4
    assert header[author_index] == "author_name"
    title_index = 5
    assert header[title_index] == "title_name"
    comment_index = 6
    assert header[comment_index] == "comments"
    url_index = 7
    assert header[url_index] == "new posting - real url"

    # While first entry of last line isn't a date
    while not ('200' in lines[-1][0] or '199' in lines[-1][0]):
        # remove the last line :)
        dropped = lines.pop()
        #print ("Dropping:", ",".join(dropped))

    converted = 0
    for i, line in enumerate(lines):
        # Verify it has the same number of columns
        if len(line) != len(header):
            print("Line is too long {}", len(line))

        action = line[comment_index]
        msg_id = line[msg_index]
        if msg_id != "":
            assert action != "", (i+2, action)

        if action == "":
            continue

        post_date = line[post_index]
        title = line[title_index]

        url = line[url_index]
        assert url.startswith("https:"), url

        if action == "ArchiveNew":
            # Check if we already downloaded & saved locally
            cache_name = "cache/" + str(msg_id) + ".html"

            print()
            print('ArchiveNew({}): "{}" from {}'.format(i+2, title, url))

            if os.path.exists(cache_name):
                with open(cache_name, "r", encoding="utf-8") as cached:
                    page_data = cached.read()

            else:
                request = urllib.request.urlopen(url)
                charset = request.info().get_content_charset()
                page_data = urllib.request.urlopen(url).read().decode(charset)
                page_data = page_data.replace(
                   '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
                   '')
                with open(cache_name, "w", encoding="utf-8") as cached:
                   cached.write(page_data)
                print ("\t Downloaded")
                time.sleep(2)
                continue
            print("\t page len:", len(page_data))

            # For now try the simpliest extraction possible
            # Assumes message starts with this string
            # and contains one internal "message-options" div
            post_start_text = '<div class="message-body">'
            post_end_text = '<div class="message-options">'
            post_start_index = page_data.index(post_start_text)
            post_end_index = page_data.index(post_end_text, post_start_index)
            print("\t source location: ", post_start_index, "to", post_end_index)
            assert post_start_index and post_end_index

            strip_comments(page_data[post_start_index: post_end_index])

            message_body = page_data[post_start_index: post_end_index] + "</div>"

            print ("\t", "{} characters copied, {:.1f}% of original html".format(
                len(message_body), 100 * len(message_body) / len(page_data)))
            print ("\t", message_body[11:55], "...", message_body[-30:])

            author = line[author_index]
            format_new_post(msg_id, title, author, post_date, message_body)

            print ()
            converted += 1
            if converted >= 40:
                # Quit after converting a couple.
                break

        elif action == "no-op":
            continue
        else:
            print("unhandled action:", action)
