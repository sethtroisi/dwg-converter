# -*- coding: utf8 -*-
import csv
import json
from array import *

import os.path
#import urllib.request
#import datetime
#import re
import sys
#import subprocess
#import time
#import tempfile
#from collections import Counter


#-----------------------

# TODO need to toggle off for final run.
ONLY_A_FEW = False
MOVING_FAST_BREAKING_THINGS = False

#------------------------

# TODO: why does this matter?
IS_LINUX = sys.platform.lower().startswith('linux')

#TODO: is this of use?
def strip_post_space(data):
    data = data.strip()

    hr_br_or_space = r'(\s*<[bh]r */?>\s*)*'
    data = re.sub(r'^' + hr_br_or_space, '', data)
    data = re.sub(hr_br_or_space + r'$', '', data)
    return data

########## MAIN ##############

INPUT_POST_JSON_FILENAME = "dwg_posts.json"
INPUT_STORIES_JSON_FILENAME = "dwg_stories.json"
OUTPUT_CSV_FILENAME = "generated_dwg.csv"
input_post_json_filename = ""
input_stories_json_filename = ""
output_csv_filename = ""
num_post_entries = 0
num_stories_entries = 0

dwg_url_prefix = "https://www.dwiggie.com"
post_url_prefix = "https://www.dwiggie.com/phorum/read.php?5,"

#Output CSV file will have columns with the names/order specified here:
#TODO have 3 urls, only need 2 - e.g. URL and archive real url are related, omit former?
#TODO posting json contains a "forum_id", and datestamp - are they relevant?? ignore for now
#TODO stories json contains a title_id, what for? num_chapters & genera is all NULL, base_url?, sub_dir? multi-part mostly blank, some null.
#TODO - these are not in same order as old archiver code so will need to alter indices in that code:
#TODO - the old "which_book" turned into 8 indiv fields, modify archiver code accordingly
csv_header = ["last_update/Posting", "create_date", "Msg Id", "author_name", "title_name", \
              "action", "FinalPost?", "category", "posting - real url", "archive real url",  \
              "northanger", "sense", "pride", "emma", "mansfield", "persuasion", "juvenilia", "misc"  \
              "Blurb", "author_id", "URL"]
post_date_index = 0
creation_date_index = 1
msg_id_index = 2
author_index = 3
title_index = 4
action_index = 5
final_post_index = 6
category_index = 7
post_url_index = 8
archive_url_index = 9
northanger_index = 10
sensibility_index = 11
prideprej_index = 12
emma_index = 13
mansfield_index = 14
persuasion_index = 15
juvenilia_index = 16
misc_index = 17
blurb_index=18
author_id_index = 19
short_url_index=20
last_csv_input_index=20

# the intermediate data structure in which to collect our data - a list of lists, 
# doing no processing so don't need to access the indiv values inside, and need all fields present to create the CSV.
output_csv = []
output_csv.append(csv_header)
next_output_csv_index = 1;

# prompt for json input filenames and output csv filename using defaults:
input_post_json_filename = input("Specify Input Post info file (default:{})?  ".format(INPUT_POST_JSON_FILENAME))
if input_post_json_filename == "":
    input_post_json_filename = INPUT_POST_JSON_FILENAME
input_stories_json_filename = input("Specify Input Stories info file (default:{})?  ".format(INPUT_STORIES_JSON_FILENAME))
if input_stories_json_filename == "":
    input_stories_json_filename = INPUT_STORIES_JSON_FILENAME
output_csv_file = input("Specify Output CSV file (default:{})?  ".format(OUTPUT_CSV_FILENAME))
if output_csv_filename == "":
    output_csv_filename = OUTPUT_CSV_FILENAME        
print("\nProcessing {} and {} to create {}\n".
      format(input_post_json_filename, input_stories_json_filename, output_csv_filename))

# process post_data file, creating corresponding entries in the csv structure:
# currently the post jsohn file is an array of 3 items - header, database, table
# table is an array of items one per post and each post is a dict with 8 keys
#TODO: what if there are non-ascii chars in here? Test?
with open(input_post_json_filename) as json_file:

    print("Post file Header info:")
    for json_file_data in json.load(json_file):     
        for key in json_file_data:
            if not (('type' in json_file_data and json_file_data['type'] == 'table') and key == "data"):
                print("table info - {}: {} ".format(key, json_file_data[key]))
            else:    # this is the array that contains 1 dict per post
                for entry in json_file_data[key]:
                    #TODO is it okay to assume that the fields are all there or do I need to verify each?
                    output_csv.append([ \
                        entry["from_unixtime(datestamp)"]   
                        , ""    # creation date
                        , entry["message_id"] 
                        , entry["author"] 
                        , entry["subject"] 
                        , "TBD" # action
                        , "TBD" # final?
                        , "TBD" # category
                        , post_url_prefix + entry["message_id"]
                        , ""    # archive url
                        , "TBD"    # assign value to only one book to call user attention to them
                        , "", "", "", "", "", "", "" 
                        , "TBD"   # blurb
                        , entry['user_id'] 
                        ])      #omitting "post" because will get that from the json later.
                    next_output_csv_index += 1
                    num_post_entries += 1
                    if ONLY_A_FEW and num_post_entries >= 5:
                        break 
          
# similarly, process the stories data file, it has the same structure as the post file but diff keys
#TODO: non-ascii chars? Test?
with open(input_stories_json_filename) as json_file:
    print("Stories file Header info:")
    for json_file_data in json.load(json_file):
        for key in json_file_data:
            if not (('type' in json_file_data and json_file_data['type'] == 'table') and key == "data"):
                print("table info - {}: {} ".format(key, json_file_data[key]))
            else:    # this is the array that contains 1 dict per story
                for entry in json_file_data[key]:
                    #TODO is it okay to assume that the fields are all there or do I need to verify each?
                    if not entry["story_url"]:
                        print("URL missing from entry {}, title id: {} in stories.json".format(num_stories_entries, entry["title_id"]))
                        continue
                    output_csv.append([ \
                          entry["last_update"]   
                        , entry["created"] 
                        , ""    # message id 
                        , entry["author_name"] 
                        , entry["title_name"] 
                        , ""    # action - none req'd
                        , entry["completed"] 
                        , entry["type"]                 #TODO - change archiver to use their values Epi, Fant, & ANI (what is?)
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
                        , entry["blurb"]   
                        , entry['user_id'] 
                        ])          #ignoring num_chapters, genera, base_url, sub_dir, multi_part
                    next_output_csv_index += 1
                    num_stories_entries += 1
                    if ONLY_A_FEW and num_stories_entries >= 5:
                        break 
 
#for i in range(next_output_csv_index):
#        print("CSV Entry({}): {}".format(i, output_csv[i]))

try:
   with open(output_csv_filename, "w", newline='') as csv_file:
      writer = csv.writer(csv_file)
      writer.writerows(output_csv)
except IOError:
    print("I/O error")

# TODO this was from an example, for dicts? determine what this means and thus if I need to do similar:  
# print("Extr:", row["color"], row.get("is_dwg", "NOT PRESENT")) # for fields maybe not present you get(field_name, DEFAULT)
  
print("""CSV file creation complete:
    {} new posts to process
    {} existing stories """.format(num_post_entries, num_stories_entries))
