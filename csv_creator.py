import csv
import json
from array import *

import os.path
import datetime
import sys

#-----------------------

# TODO need to toggle off for final run.
ONLY_A_FEW = False

#------------------------

########## MAIN ##############

PREVIOUS_ARCHIVE_DATE = datetime.datetime(2019,7,1)	# will ignore any messages older than this as they've already been processed
CURRENT_ARCHIVE_DATE = datetime.datetime(2021, 8,23)    
	# this is the final date included in this archive, becomes next "PREVIOUS_ARCHIVE_DATE"
comparison_date = int(PREVIOUS_ARCHIVE_DATE.timestamp())     #should be a unixtime but apparently a float so force it to int

MSG_BOARD_FORUM_ID = "5"
ANI_MSG_FORUM_ID = "6"
TOP_LEVEL_MSG = "0"
INPUT_POSTS_JSON_FILENAME = "data/dwg_posts.json"     
        # forum content, possibly thru all time, all forums, so needs to be pruned
INPUT_STORIES_JSON_FILENAME = "data/dwg_stories.json"
	# this is the current master story index into which to merge our new entries
OUTPUT_INDEX_FILENAME = "data/generated_dwg_index.csv"
input_posts_json_filename = ""
input_stories_json_filename = ""
output_index_filename = ""
output_posts_filename = ""
num_post_entries = 0
num_ANI_entries = 0
num_stories_entries = 0

dwg_url_prefix = "https://www.dwiggie.com"
post_url_prefix = "https://www.dwiggie.com/phorum/read.php?5,"

#Output index CSV file will have columns with the names/order specified here:
index_csv_header = ["last_update/Posting", "create_date", "Msg Id", "author_name", "title_name",
              "action", "FinalPost?", "category", "posting - real url", "archive real url",
              "northanger", "sense", "pride", "emma", "mansfield", "persuasion", "juvenilia", "misc", "author_id", "email",
              "Blurb"]

# the intermediate data structure in which to collect our index data - a list of lists,
# doing no processing so don't need to access the indiv values inside, and need all fields present to create the CSV.
output_index = []
output_index.append(index_csv_header)
next_output_index_index = 1;

# prompt for json input filenames and output csv filename using defaults:
input_posts_json_filename = input("Specify Input Post info file from dwiggiec_dwg->phorum msgs(default:{}):  ".format(INPUT_POSTS_JSON_FILENAME))
if input_posts_json_filename == "":
    input_posts_json_filename = INPUT_POSTS_JSON_FILENAME
input_stories_json_filename = input("Specify Input Stories info file from dwiggiec_dwg->dwg_stories (default:{}):  ".format(INPUT_STORIES_JSON_FILENAME))
if input_stories_json_filename == "":
    input_stories_json_filename = INPUT_STORIES_JSON_FILENAME
output_index_filename = input("Specify Output Index file (default:{}):  ".format(OUTPUT_INDEX_FILENAME))
if output_index_filename == "":
    output_index_filename = OUTPUT_INDEX_FILENAME
print("\nProcessing entries newer than {}\n\t from {} and {}\n\t to create index {}\n".format(
    PREVIOUS_ARCHIVE_DATE, input_posts_json_filename, input_stories_json_filename, output_index_filename))

# process post_data file, creating corresponding entries in the csv structure:
# currently the post jsohn file is an array of 3 items: header, database ("dwiggiec_dwg"), table "phorum_messages"
# the table is an array of items one per post and each post is a dict with many keys.
# The posts are for several diff forums, so filter for the message board and ANI ids
# Message Board posts have 24 keys but we don't need many of them.
# These posts are nested and we only want top one so that needs to be decoded:
#   "parent_id"==0 appears to designate the top of level of nested posts with
#    a shared "thread" value for related message and parent_id==the "thread" of the parent msg
# Here are the post fields I make no use of: thread", user_id", ip", "status",
#   "msgid", modifystamp", "thread_count", "moderator_post", sort", "meta", "viewcount",
#   "threadviewcount", "closed", "recent_message_id", "recent_user_id", "recent_author", "moved"


#TODO: what if there are non-ascii chars in here? Test?
with open(input_posts_json_filename) as json_file:

    print("Post file Header info:")
    for json_file_data in json.load(json_file):
        for key in json_file_data:
            if not (('type' in json_file_data and json_file_data['type'] == 'table') and key == "data"):
                print("\ttable info - {}: {} ".format(key, json_file_data[key]))
                #TODO: could verify that table data, name="phorum_messages") AND "database"= "dwiggiec_dwg"
            else:
                # this is the data array that contains 1 dict per post
                for entry in json_file_data[key]:           

                    if not (((entry["forum_id"] == MSG_BOARD_FORUM_ID) or (entry["forum_id"] == ANI_MSG_FORUM_ID))
                           and (entry["parent_id"] == TOP_LEVEL_MSG) 
                           and (int(entry["datestamp"]) >= comparison_date)):
                        #TODO remove the following conditional test after 8/2021 archive, it temporarily
                        #gives pass to all ANI items because haven't been many haven't been processed    
                        if not ((entry["forum_id"] == ANI_MSG_FORUM_ID) and (entry["parent_id"] == TOP_LEVEL_MSG)):  
                            continue

                    if entry["forum_id"] == MSG_BOARD_FORUM_ID:
                         output_index.append([ \
                            datetime.date.fromtimestamp(int(entry["datestamp"]))
                            , ""    # creation date
                            , entry["message_id"]
                            , entry["author"]
                            , entry["subject"]
                            , "TBD" # action
                            , "0" # final   #assume not until learn otherwise
                            , "epi" # assume most likely case
                            , post_url_prefix + entry["message_id"]
                            , ""    # archive url
                            , "", "", "1", "", "", "", "", ""  # assign most likely book for minimum mods later
                            , entry['user_id']
                            , entry['email']
                            , "TBD"   # blurb
                            ])      #omitting "post", see below
                         num_post_entries += 1
                        
                    if entry["forum_id"] == ANI_MSG_FORUM_ID:
                        output_index.append([ \
                            datetime.date.fromtimestamp(int(entry["datestamp"]))
                            , ""    # creation date
                            , entry["message_id"]
                            , entry["author"]
                            , entry["subject"]
                            , "TBD" # action
                            , "0" # final   #assume not until learn otherwise
                            , "ANI"
                            , post_url_prefix + entry["message_id"]
                            , ""    # archive url
                            , "", "", "", "", "", "", "", ""  # all irrelevant for ANI
                            , entry['user_id']
                            , entry['email']
                            , "TBD"   # blurb
                            ])      #omitting "post" because the archiver wants to edit the text which relies on
                                    # having complete html not found here. this could be changed in the future.
                        num_ANI_entries += 1
                                                  
                    next_output_index_index += 1
                    if ONLY_A_FEW and next_output_index_index >=5:
                        break                   

# similarly, process the stories data file, it has the same structure as the post file but diff keys
#TODO: non-ascii chars? Test?
with open(input_stories_json_filename) as json_file:
    print("Stories file Header info:")
    for json_file_data in json.load(json_file):
        for key in json_file_data:
            if not (('type' in json_file_data and json_file_data['type'] == 'table') and key == "data"):
                print("\ttable info - {}: {} ".format(key, json_file_data[key]))
            else:    # this is the array that contains 1 dict per story
                for entry in json_file_data[key]:
                    #TODO is it okay to assume that the fields are all there or do I need to verify each?
                    if not entry["story_url"]:
                        print("URL missing from entry {}, title: {} in stories.json".format(num_stories_entries, entry["title_name"]))
                        #TODO num_stories_entries in previous print statement needs to be the index of the current loop
                        continue
                    output_index.append([ \
                          entry["last_update"]
                        , entry["created"]
                        , ""    # message id
                        , entry["author_name"]
                        , entry["title_name"]
                        , ""    # action - none req'd
                        , entry["completed"]
                        , entry["type"]                 
                        , ""    # posturl
                        , dwg_url_prefix + entry["story_url"]
                        , entry["northanger"]
                        , entry["sense"]
                        , entry["pride"]
                        , entry["emma"]
                        , entry["mansfield"]
                        , entry["persuasion"]
                        , entry["juvenilia"]
                        , entry["misc"]
                        , entry['user_id']
                        , ""   # email doesn't exist in this file
                        , entry["blurb"]
                        ])          #ignoring num_chapters, genera, base_url, sub_dir, multi_part
                    num_stories_entries += 1
                    next_output_index_index += 1
                    if ONLY_A_FEW and next_output_index_index >=5:
                        break

#for i in range(next_output_index_index):
#        print("CSV Entry({}): {}".format(i, output_index[i]))

try:
   with open(output_index_filename, "w", newline='') as csv_file:
      writer = csv.writer(csv_file)
      writer.writerows(output_index)
except IOError:
    print("I/O error")


# TODO this was from an example, for dicts? determine what this means and thus if I need to do similar:
# print("Extr:", row["color"], row.get("is_dwg", "NOT PRESENT")) # for fields maybe not present you get(field_name, DEFAULT)

assert(num_post_entries+num_ANI_entries+num_stories_entries == len(output_index)-1)
print("""CSV index file creation complete:
    {} new message board posts to process
    {} new ANI posts to process
    {} have existing story entries """.format(num_post_entries, num_ANI_entries, num_stories_entries))
