import json
import os
import re


from bs4 import BeautifulSoup

import subprocess
#output = subprocess.check_output(["notepad", "test.txt"])


# temp = data.replace("\n\n\n\n", "\n").replace("\n\n\n", "\n")
ANCHOR_FINDER = re.compile('<a *name="*([a-z0-9-]*)"* *\?>')

def save_html(file_path, soup):
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(str(soup))

def get_changes(file_path, file_data):
    # TODO verify that soup doesn't change message body too dramatically.
    soup = BeautifulSoup(file_data, "html.parser")

    bodies = soup.find_all(class_="message-body")
    assert len(bodies) == 1, len(bodies)
    body = bodies[0]

    #temp:
    #import pdb; pdb.set_trace()

    # remove message options from bottom of post
    #TODO - need to catch errors here due to "bad" html
    body.find(class_="message-options").extract()

    file_actions = []

    children = []
    for i, child in enumerate(body.recursiveChildGenerator()):
        if i == 24:
            break

        children.append(child)

        content = str(child)

        depth = 1
        n = child
        while n.parent != body:
            depth += 1
            n = n.parent

        name = child.name if child.name else "<NONE>"
        print("{:2}{}{:8} {:4} | {}".format(
            i, "\t" * depth, name, len(content), content[:60]))

    print()
    print()
    print("D: [D]one with this file")
    print("r: [R]evert all deletes")
    print("q: [Q]uit (be done for now)")
    print()
    while True:
        action = input("drq|<line>|<line>-<line>: ").lower()
        if action == "d":
            new_path = file_path.replace(".html", ".soup.html")
            #print("Done with this file! Saving as", new_path)
            print("Done with this file! *****************************************")
            save_html(new_path, body)
            return file_actions, str(body)
        elif action == "r":
            print("Reverting and restarting")
            return None, None
        elif action == "q":
            print("Quitting story_fixer for now!")
            return "QUIT", None

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
            node = children[c]

            if c == first:
                # replace child in doc with empty AUTHOR_NOTE tag.
                node.replace_with(dna_tag)
            else:
                node.extract()

            # place child inside dna tag.
            dna_tag.append(node)

            file_actions.append(((first, last), str(node)))
            print("Encapsulating:", str(node)[:60])


#-------------------

TO_FIX_DIR = "cache/"
POST_REGEX = r'^[0-9]+.html$'

for fn in sorted(os.listdir(TO_FIX_DIR)):

    #TODO TEMP To determine error:
    #if fn != '126607.html':
    #   continue

    if re.match(POST_REGEX, fn):
        file_path = TO_FIX_DIR + "/" + fn

        #assume any exisiting file is already processed and skip it:
        soup_path = file_path.replace(".html", ".soup.html")
        if os.path.exists(soup_path):
            print(file_path + " already processed")
            continue

        with open(file_path, encoding="utf-8") as forum_file:
            data = forum_file.read()

        print()
        print(fn, len(data))

        file_actions, new_data = get_changes(file_path, data)
        print("\t", file_actions)

        while file_actions == new_data == None:
            # revert: retry
            file_actions, new_data = get_changes(file_path, data)

        if file_actions == "QUIT":
            break
