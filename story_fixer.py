import json
import os
import re
import sys

from bs4 import BeautifulSoup

import subprocess
#output = subprocess.check_output(["notepad", "test.txt"])

CACHE_DIR = "cache/"
POST_REGEX = r'^[0-9]+.html$'

ANCHOR_FINDER = re.compile('<a *name="*([a-z0-9-]*)"* *\?>')


def save_html(file_path, body_str):
    data = body_str
    if len(data) // (1 + data.count("\n")) > 300:
        print ("Adding newlines", data.count("<br/>"))
        data = data.replace("<br/>", "<br/>\n")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(data)


def select_dna(soup, body, children, part):
    for i, child in children:
        content = str(child)

        depth = 1
        n = child
        while n.parent != body:
            depth += 1
            n = n.parent

        name = child.name if child.name else "<NONE>"
        short_line = content
        if len(content) >= 100:
            short_line = content[:57] + "..." + content[-40:]

        print ("{:2}{}{:8} {:4} | {}".format(
            i, "\t" * depth, name, len(content), short_line))

    file_actions = []

    print()
    print()
    print("D: [D]one with {} of file".format(part))
    print("r: [R]evert all deletes")
    print("q: [Q]uit (be done for now)")
    print()
    while True:
        action = input("drq|<line>|<line>-<line>: ").lower()
        if action == "d":
            return True, file_actions
        elif action == "r":
            print("Reverting and restarting")
            return False, None
        elif action == "q":
            print("Quitting story_fixer for now!")
            sys.exit()

        # Match "<line>" or "<line>-<line>"
        valid_action = re.match("(\d+)(?:-(\d+))?", action, re.I)
        if not valid_action:
            print("Bad action: \"{}\"".format(action))
            continue

        groups = list(valid_action.groups())
        if groups[1] is None:
            groups[1] = groups[0]

        first, last = list(map(int, groups))

        dna_tag = soup.new_tag("dna")

        for c in range(first, last+1):
            for i, node in children:
                if i == c:
                    if c == first:
                        # replace child/node in doc with empty AUTHOR_NOTE tag.
                        node.replace_with(dna_tag)
                    else:
                        node.extract()

                    # place child/node inside dna tag.
                    dna_tag.append(node)

                    file_actions.append(((first, last), str(node)))
                    print("Encapsulating:", str(node)[:60])
                    break
            else:
                print("Didn't find line", c, "REVERTING")
                return False, None
        print()


def get_changes(file_path, file_data):
    # TODO verify that soup doesn't change message body too dramatically.
    soup = BeautifulSoup(file_data, "html.parser")

    bodies = soup.find_all(class_="message-body")
    assert len(bodies) == 1, len(bodies)
    body = bodies[0]

    # Remove message options from bottom of post
    body.find(class_="message-options").extract()

    children = []
    for i, child in enumerate(body.recursiveChildGenerator()):
        children.append((i, child))

    print ("*" * 80)
    print ("Start of", file_path, len(file_data), "characterss")

    # First 26 lines
    status, file_actions1 = select_dna(soup, body, children[:26], "top")
    if not status:
        # Revert or Quit
        return status

    # Last 16 lines
    status, file_actions2 = select_dna(soup, body, children[-16:], "end")
    if not status:
        return status

    file_actions = file_actions1 + file_actions2

    # TODO: consider adding a confirmation on leaving in "To Be Continued", "The End", "Fin"
    edit_message = "Last edit at"
    edit_was_present = edit_message in str(body)
    edit_was_removed = any(edit_message in action[1] for action in file_actions)

    assert (not edit_was_present) or edit_was_removed, (
        edit_was_present, edit_was_removed, file_actions)

    new_path = file_path.replace(".html", ".soup.html")
    save_html(new_path, body.prettify())

    print ("\tActions:", file_actions)

    print ("Done with this file!")
    print ("*" * 80)

    return True


#-------------------

def fix_one_file(file_name):
    file_path = CACHE_DIR + "/" + file_name
    assert os.path.exists(file_path), file_name + " should exist before we try to fix it"

    #assume any exisiting file is already processed and skip it:
    soup_path = file_path.replace(".html", ".soup.html")
    if os.path.exists(soup_path):
        print (file_path + " already processed")
        return True

    with open(file_path, encoding="utf-8") as forum_file:
        # Break file over many lines
        data = forum_file.read()

    print ()
    while True:
        status = get_changes(file_path, data)
        if status:
            return status
        # Retrying.
        pass


def all_at_once():
    for file_name in sorted(os.listdir(CACHE_DIR)):
        if re.match(POST_REGEX, file_name):
            fix_one_file(file_name)


if __name__ == "__main__":
    all_at_once()
