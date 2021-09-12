# dwg-converter
Scripts to help convert forum posts to stories
in process of update 8/2021 - blt

This whole repository is rapidly changing. The documentation is out of date or wrong in many places, sorry.

## Overview

Take
 * forum posts (e.g. [To the Lakes](https://www.dwiggie.com/phorum/read.php?5,124030)) and turn them into archived stories by collating the text (which may be spread across multiple forum posts) into a new, correctly named file, editing out any extraneous or "dna" material then adding the story to the correct index and moving the new file to the correct directory on dwiggie.
 * would love to move multi-post stories (e.g. [An Unwanted Engagement](https://www.dwiggie.com/derby/jessil1b.htm)) into single page stories but that doesn't look like happening.

## Artifacts (update this section)

**`dwg-posts-2019-01-26.csv`** is the cannonical input csv it was downloaded from the Google Spreadsheet on 2019-01-26 and information about urls, authors, titles, ...
  * The complete header is ```last_update/Posting,date_created,Msg Id,author_id,author_name,title_name,comments,new posting - real url,archive real url,FinalPost?,WhichBook?,Archive Title,Archive Title ID,URL,```

**`templates/story_archive_template.html`** Best guess at the historical template used to archive forum posts
  * `back.gif` and `stories.css` are referenced here

**`templates/story_joined_template.html`** Template for joining multitple stories

**`post_datas.json`** Cache of data created by reading stories in `story_extract.py`, used to avoid reprocessing each time.

**`url_data.json`** Data about url created by `story_fetcher.py`, read by `story_extract.py`

**`stories_raw/`**: A local cache of all stories is created here

**`stories/`**: A local cache of stories with guess at encoding

**`story_backup/`**: ??? Is this used in the workflow?

## Scripts

Several helper scripts exist

**`csv_creator.py`**: converts forum post json to corresponding csv

**`story_archiver.py`**: Downloads forum post

**`story_fetcher.py`**: Download all existing stories

**`story_extract.py`** Extract content of story

**`extra.py`**

**`utils.py`**

## Workflows

```
# Go to dwiggie server php_***** and:
#	- export forum data (cpanel: dwiggiec_dwg->phorum_messages) to local file, dwg_posts.json
#	- export master story index (cpanel: dwiggiec_dwg->dwg_stories) to local file, dwg_stories
# edit csv_creator to update the current and previous archive date constants
# run csv_creator to convert the two jsons to a corresponding, merged index csv.
# import that index csv into a spread sheet (google sheets avoids some Excel char set issues):
#	- sort the entries by date and highlight all the new entries
#	- resort by author/story title and ensure:
#	   that the story parts sequence using IDENTICAL author names and titles
#	        (title text following "::" is ignored, allowing for e.g. "Chapter n")  
#	      watch out for posts that are continuations of previously archived stories
#	   the correct action is chosen - e.g. new vs append
#	   look at each post to determine:
# 		the story category and book
#		the story_final value is correctly specified
#		copy any blurb included with any keyword other than "blurb" 
#	   that the url of the entry before the first AppendArchive is actually the final page of any multipage story else... 
# export the spreadsheet to a new csv which will be input to story_archiver
#run story archiver which requires the modified CSV and also the dwg_stories json file.
#    - use a large shell window in order to best view the required editing lines for each post file:
#    - the "editor' allows you to nominate line ranges (e.g. "0-5") which will be removed from final text
#          specify all dna, extraneous author notes, title, author notes
#	   if author specified a DNA/RA pair, must include the matched set in the deletion selection
#	   blurbs will be extracted before stripping so if inside dna, don't worry but ensure that blurbs are deliminted with a <BR>
#	   watch out for formatting e.g. <span> stuff, sometimes that is on first line, don't delete it or will crash
#	   also crashes if specify, seperately, two adjacent lines!
#    - as each file appears for edit, I cross ref agst the web page to ensure nothing outside my view is amiss. 
#         sometimes I have to edit the soup.html to fix things 
#    - appending to old archive files that are not in the new format requires a trip to a pop-up editor.
#	   In this case, you need to rearrange some markers at the beginning and end of file in very particular ways
#		as documented in the ensure_new_format procedure. Takes some trial and error the first time!
#    - to rerun and recreate append-to-archive stories, must delete the original url file else skips. 
# review the output csv file to ensure that all entries are complete, in particular, the blurbs. 
#	Blurb processing is easily defeated by the random things that authors do so modify the soup file or edit csv
#	If blurbs are missing, manually add one to the modified_csv and that will carry over to the output

# Need to change the template file path in the html before done - either rerun (deleting and rediting append to archive files)
#	or run some magic linux cmd. 
# Review the generated story files to ensure that they look correct:
#	For stories with many updates, might want to manually prune most of the jump links
# Review the output csv file and ensure that all the entries are complete. Can edit this rather than rerunning. Just don't subsequently overwrite!
# Review the csv.tbd file and act as necessary on any items in there

# Run csv_to_sql to generate the necessary sql statements to apply agst the TOC db and segregate the files to xfer. 
#TBD instructions to write the story files out to dwiggie_c?
#TBD  the new story files go to /2019 or new dir each time? 
#   the appended story files back to their original locations as specified in the csv
#TBD do we need to worry about file permissions or other attributes?
# TBD: how do the sql statements get applied?

# execute any other instructions from the story_archiver output e.g. deleting stories or posts


#Review/update this - still relevant? or was this an attempt to merge multi page stories??:
# Download all stories locally, creates stories_raw/ and stories/
# Saves a map of URL => local file in url_data.json
# e.g. "https://www.dwiggie.com/derby/olde/gabby1.htm" => "99cc07d1fcb85292819b4766922081e6.html")
python story_fetcher.py

# Extract post metadata and story into post_datas.json
python story_extract.py regenerate

# Subsequent story_extract.py don't need to read all post data again
python story_extract.py
```

