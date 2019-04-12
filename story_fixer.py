import json
import os
import re

from bs4 import BeautifulSoup


def get_changes(file_data):
    # TODO verify that soup doesn't change message body to dramatically
    soup = BeautifulSoup(file_data, "html.parser")

    bodies = soup.find_all(class_="message-body")
    assert len(bodies) == 1, len(bodies)
    body = bodies[0]

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
            print("Done with this file!")
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
            groups = [groups[0], groups[0]]

        groups = list(map(int, groups))
        first, last = groups

        for c in range(first, last+1):
            node = children[c].extract()
            file_actions.append(("d", str(node)))
            print("Deleting:", str(node)[:60])


#-------------------


TO_FIX_DIR = "cache/"
POST_REGEX = r'^[0-9]+.html$'

STORY_FIXES = "story_fixes.json"

# TODO(brenda): restore and ignore stories in story_fixes.json

# story to node text deleted
fixes = {}

for fn in os.listdir(TO_FIX_DIR):
    if re.match(POST_REGEX, fn):
        with open(TO_FIX_DIR + "/" + fn) as forum_file:
            data = forum_file.read()

        print()
        print(fn, len(data))

        file_actions, new_data = get_changes(data)
        print("\t", file_actions)

        while file_actions == new_data == None:
            # revert: retry
            file_actions, new_data = get_changes(data)

        if file_actions == "QUIT":
            break


        fixes[fn] = file_actions

# Save changes
with open(STORY_FIXES, "w") as fixes_file:
    json.dump(fixes, fixes_file)
