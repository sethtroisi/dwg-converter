# Quick and dirty

with open("data/the_end_filenames.txt") as f:
    finished_stories = set()
    for line in f:
        line = line.strip()
        if line: # ignore blank lines
            finished_stories.add(line)

# First 5 stories
print(len(finished_stories), "stories with \"the end\"")
print(sorted(finished_stories)[:5])
print()

with open("data/story_status.txt") as f:
    story_status = {}
    for line in f:
        line = line.strip("| \n") # removing "|" and any leading spaces
        if "/derby" in line:
            story, status = line.split("|")
            story = story.strip().replace("/derby/", "")
            status = status.strip()

            if story in finished_stories:
                finished_stories.remove(story)
                if status != "1":
                    print (story, status)

print()
print(len(finished_stories), "stories didn't have db entries (probably multipart stories)")

