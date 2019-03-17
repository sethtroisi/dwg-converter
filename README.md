# dwg-converter
Scripts to help convert forum posts to stories

This whole repository is rapidly changing. The documentation is out of date or wrong in many places, sorry.

## Overview

Take
 * forum posts (e.g. [To the Lakes](https://www.dwiggie.com/phorum/read.php?5,124030))
 * multi-page stories (e.g. [An Unwanted Engagement](https://www.dwiggie.com/derby/jessil1b.htm))
And combine them into single page stories

## Artifacts

**`dwg-posts-2019-01-26.csv`** is the cannonical input csv it was downloaded from the Google Spreadsheet on 2019-01-26 and information about urls, authors, titles, ...
  * The complete header is ```last_update/Posting,date_created,Msg Id,author_id,author_name,title_name,comments,new posting - real url,archive real url,FinalPost?,WhichBook?,Archive Title,Archive Title ID,URL,```

**`story_archive_template.html`** Best guess at the historical template used to archive forum posts

**`story_joined_template.html`** Template for joining multitple stories

**`post_datas.json`** Cache of data created by reading stories in `story_extract.py`, used to avoid reprocessing each time.

**`url_data.json`** Data about url created by `story_fetcher.py`, read by `story_extract.py`

**`stories_raw/`**: A local cache of all stories is created here

**`stories/`**: A local cache of stories with guess at encoding

**`story_backup/`**: ??? Is this used in the workflow?

## Scripts

Several helper scripts exist

**`story_archiver.py`**: Downloads forum posts

**`story_fetcher.py`**: Download all existing stories

**`story_extract.py`** Extract content of story

**`extra.py`**

**`utils.py`**

## Workflows

```
  # Run 

