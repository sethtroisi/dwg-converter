# -*- coding: utf8 -*-

# This reads story_archiver's output csv and creates the corresponding sql statements
#   (insert for new stories and update for appended stories) to update the story_TOC.
# It also segregates and copies the corresponding story files to two /cache subdirs and prints
#   the associated filenames to facilitate their transfer over to dwiggie. 


import csv
import os.path
#from shutil import copyfile
import shutil
from collections import Counter

DWG_DIR = 'derby'
INPUT_CSV_FILENAME = "data/dwg_archive_results.csv"  # output from story_archive, manually touched up
OUTPUT_SQL_FILENAME = "data/dwg_archive_results.sql"    #output instructions to use at dwiggie_c
input_csv_filename = ""
output_sql_filename = ""
story_file_dir = "cache"
new_file_dir = story_file_dir+"/new_files"
updated_file_dir= story_file_dir+"/updated_files"

#Input CSV file should have the following columns, specified in csv_creator and passed on by story_archiver:
header_test = ['last_update/Posting','create_date','Msg Id','author_name','title_name',
               'action','FinalPost?','category','posting - real url','archive real url',
               'northanger','sense','pride','emma','mansfield','persuasion','juvenilia','misc',
               'author_id','email','Blurb','New Filename'
]
'''
sample_entry = ["2019-07-13","2019-07-13","128413","Alicia M.","At Pemberly",
               "ArchiveNew","1","Epi","https://www.dwiggie.com/phorum/read.php?5,128413",,,,"1",,,,,,
               "0",,"A short, silly conversation during Elizabeth's Pemberley visit.",
               "AliciaMAtPemberly20190713.htmlpost_date_index = 0
]'''
post_date_index = 0
creation_date_index = 1
msg_id_index = 2
author_index = 3
title_index = 4
action_index = 5
final_post_index=6
category_index = 7
post_url_index = 8
archive_url_index = 9
northanger_index = 10
sense_index = 11
pride_index = 12
emma_index = 13
mansfield_index = 14
persuasion_index = 15
juvenilia_index = 16
misc_index = 17
author_id_index = 18
email_index = 19
blurb_index=20
new_filename_index=21
last_csv_input_index=21

#----------------
 
sql_schema =  """
  title_name varchar(255),
  title_id int(20) NOT NULL AUTO_INCREMENT,
  story_url varchar(255),
  author_name varchar(100)
  user_id int(10),
  type enum('Epi','Fant','ANI'),
  blurb text,
  northanger tinyint(1), sense tinyint(1), pride tinyint(1), emma tinyint(1),
  mansfield tinyint(1), persuasion tinyint(1), juvenilia tinyint(1), misc tinyint(1),
  created date,
  last_update date,
  num_chapters int(5),
  completed tinyint(1),
  genera varchar(255),
  base_url varchar(20),
  sub_dir varchar(30),
  multi_part tinyint(1),
  PRIMARY KEY (title_id)
"""

# SQL statement templates:
SQL_INSERT_TEMPLATE = '''
        INSERT INTO dwg_stories (title_name, story_url, author_name, user_id, type, blurb,
                                northanger, sense, pride, emma, mansfield, persuasion, juvenilia,
                                misc, created, last_update, completed, base_url, sub_dir)
        VALUES (
            {title_name},
            '{story_url}',
            '{author_name}',
            {user_id},
            '{category}',
            {blurb},
            {northanger},
            {sense},
            {pride},
            {emma},
            {mansfield},
            {persuasion},
            {juvenilia},
            {misc},
            '{created_date}',
            '{last_update}',
            {completed},
            '{base_url}',
            '{sub_dir}'
        );'''

SQL_UPDATE_TEMPLATE = '''
        UPDATE dwg_stories
        SET
            blurb = {blurb},
            northanger = {northanger},
            sense = {sense},
            pride = {pride},
            emma = {emma},
            mansfield = {mansfield},
            persuasion = {persuasion},
            juvenilia = {juvenilia},
            misc = {misc},
            last_update = '{last_update}',
            completed = {completed}
        WHERE title_name = {title_name} AND author_name = '{author_name}';
        '''
        
def bad_sql_escape(text):
    return "'" + text.strip().replace("'", "''") + "'"

def generate_sql_statement(action, line):  

    # This is how sql escapes things
    blurb = bad_sql_escape(line[blurb_index])
    title = bad_sql_escape(line[title_index])
    
    # Note, new stories are not multipart

    if action == "ArchiveNew":
        base_url = os.path.splitext(os.path.basename(line[new_filename_index]))[0]
        story_url = '/' + DWG_DIR + '/'+ dwq_archive_dir + '/' + line[new_filename_index]
   
        #TODO: wanted to use DEFAULT rather than NULL but sqlite didn't accept, does dwg?
        sql_statement = SQL_INSERT_TEMPLATE.format(
            title_name = title,
            story_url = story_url,
            author_name = line[author_index],
            user_id = line[author_id_index] if line[author_id_index]  else "NULL",
            category = line[category_index],
            blurb = blurb,
            northanger = line[northanger_index] if line[northanger_index] else "NULL",
            sense = line[sense_index] if line[sense_index] else "NULL",
            pride = line[pride_index] if line[pride_index] else "NULL",
            emma = line[emma_index] if line[emma_index] else "NULL",
            mansfield = line[mansfield_index] if line[mansfield_index] else "NULL",
            persuasion = line[persuasion_index] if line[persuasion_index] else "NULL",
            juvenilia = line[juvenilia_index] if line[juvenilia_index] else "NULL",
            misc = line[misc_index] if line[misc_index] else "NULL",
            created_date = line[creation_date_index],
            last_update = line[post_date_index],
            completed = line[final_post_index],
            base_url = base_url,
            sub_dir = dwq_archive_dir)
  
    elif action == "AppendArchive":
        # be very careful with this statement! WHERE must be precise so as to not overwrite multiple entries!
        # We're safe overwriting all the fields because we just fetched the values from the db.
        # We only specify the few columns that CAN change
        #   by definition, title_name, author_name DON'T change and story_url CAN'T change: 
        sql_statement = SQL_UPDATE_TEMPLATE.format(
            title_name = title,
            author_name = line[author_index],
            type = line[category_index],
            blurb = blurb,
            northanger = line[northanger_index] if line[northanger_index] else "NULL",
            sense = line[sense_index] if line[sense_index] else "NULL",
            pride = line[pride_index] if line[pride_index] else "NULL",
            emma = line[emma_index] if line[emma_index] else "NULL",
            mansfield = line[mansfield_index] if line[mansfield_index] else "NULL",
            persuasion = line[persuasion_index] if line[persuasion_index] else "NULL",
            juvenilia = line[juvenilia_index] if line[juvenilia_index] else "NULL",
            misc = line[misc_index] if line[misc_index] else "NULL",
            last_update = line[post_date_index],
            completed = line[final_post_index])
        
    else: assert True, 'Unknown action in sql - code error'
    
    return sql_statement


####### main *******

input_csv_filename = input("Specify manually edited CSV action file (default:{}):  ".format(INPUT_CSV_FILENAME))
if input_csv_filename == "":
    input_csv_filename = INPUT_CSV_FILENAME
output_sql_filename = input("Specify Output CSV file (default:{}):  ".format(OUTPUT_SQL_FILENAME))
if output_sql_filename == "":
    output_sql_filename = OUTPUT_SQL_FILENAME

dwq_archive_dir = ""
while not dwq_archive_dir:
    dwq_archive_dir = input("name of archive subdir at dwiggie_c: ")

new_filelist = ['Files in ' + new_file_dir  + ' to write to /derby' + dwq_archive_dir+':']
archive_filelist = ['Files in ' + updated_file_dir + ' to overwrite at dwiggie:']

os.makedirs(new_file_dir + '/',exist_ok=True)
os.makedirs(updated_file_dir + '/',exist_ok=True)

with open(input_csv_filename) as csv_file:
    reader = csv.reader(csv_file)
    lines = list(reader)

header = lines.pop(0)
#print ("\n{} files to process: \n".format(len(lines)))

assert header == header_test, header

c = Counter()
with open(output_sql_filename, "w") as sql_file:
    for line in lines:
        action = line[action_index]
        c[action] += 1

        sql_statement = generate_sql_statement(action, line)
        #print (sql_statement)

        source_file = story_file_dir+"/"+line[new_filename_index]

        if action == "ArchiveNew":
            target_file = new_file_dir+'/'+line[new_filename_index]
            shutil.copyfile(source_file, target_file)
            #new_url = 'https://www.dwiggie.com/derby/'+dwq_archive_dir+'/'+line[new_filename_index]
            new_filelist.append(line[new_filename_index])

        elif action == "AppendArchive":
            target_file = updated_file_dir+'/'+line[new_filename_index]
            shutil.copyfile(source_file, target_file)
            # Need to keep matched pairs of file to destination for this set:
            archive_filelist.append(target_file)
            archive_filelist.append(line[archive_url_index])

        else:
            print("Unexpected action", action, line)
            continue

        sql_file.write(sql_statement + "\n")

#TODO should we write these to a file?
print('ensure that these files get written to dwiggie.com: \n')
print(new_filelist)
print()
print(archive_filelist)
print('\nNumber of files to process: ')
print(c)
