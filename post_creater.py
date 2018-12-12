import csv
import os.path
import time
import urllib.request

CSV_PATH = "2018-12-08-dwg-values.csv"
ARCHIVE_TEMPLATE = "archive_template.html"


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

def format_post(msg_id, title, author, post_date, post):
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
        .replace("$COPYRIGHT_YEAR", post_date[-4:]))


    # TODO 4 letters of author name + number?
    output_name = "cache/" + str(msg_id) + ".converted.html"
    with open(output_name, "w") as output_file:
        output_file.write(new_story)

    print("\t wrote {} to {}".format(
        len(new_story), output_name))


########## MAIN ##############

if not os.path.exists("cache"):
        os.makedirs("cache")

with open(CSV_PATH) as csv_file:
    csv_reader = csv.reader(csv_file)
    lines = list(csv_reader)

    print("Lines: {}, length of first line: {}".format(
        len(lines), len(lines[0])))
    print()

    header = lines.pop(0)

    # Join each item in the list with ', ' and print
    print(", ".join(header))
    print()

    # We are going to need to look up new url a lot
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
            assert action != "", (i+2, line)

        if action == "":
            continue

        title = line[title_index]

        url = line[url_index]
        assert url.startswith("https:"), url

        if action == "ArchiveNew":
            # Check if we already downloaded & saved locally
            cache_name = "cache/" + str(msg_id) + ".html"

            print()
            if os.path.exists(cache_name):
                with open(cache_name, "r") as cached:
                    page_data = cached.read()
            else:
                page_data = urllib.request.urlopen(url).read().decode("utf-8")
                page_data = page_data.replace(
                    '<script type="text/javascript" src="https://www.dwiggie.com/phorum/javascript.php?5"></script>',
                    '')

                with open(cache_name , "w") as cached:
                    cached.write(page_data)
                print ("Downloaded")
                time.sleep(5)

            print('ArchiveNew({}): "{}" from {}'.format(i+2, title, url))
            print("\t", len(page_data))

            # For now try the simpliest extraction possible
            # Assumes message starts with this string
            # and contains one internal "message-options" div
            post_start_text = '<div class="message-body">'
            post_end_text = '<div class="message-options">'
            post_start_index = page_data.index(post_start_text)
            post_end_index = page_data.index(post_end_text, post_start_index)
            print("\t", post_start_index, "to", post_end_index)
            assert post_start_index and post_end_index

            message_body = page_data[post_start_index: post_end_index] + "</div>"

            print ("\t", "{} characters, {:.1f}% of html".format(
                len(message_body), 100 * len(message_body) / len(page_data)))
            print ("\t", message_body[:40], "...", message_body[-30:])

            author = line[author_index]
            format_post(msg_id, title, author, line[0], message_body)

            print ()
            converted += 1

        elif action == "no-op":
            continue
        else:
            print("unhandled action:", action)
