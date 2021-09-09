# -*- coding: utf8 -*-
import csv
import os.path

DWG_DIR = 'derby'
INPUT_CSV_FILENAME = "data/dwg_archive_results.csv"  # output from story_archive, manually touched up
OUTPUT_SQL_FILENAME = "data/dwg_archive_results.sql"    #output instructions to use at dwiggie_c
input_csv_filename = ""
output_sql_filename = ""

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
        INSERT INTO dwg_stories VALUES ("
            {title_name},
            NULL,
            {story_url},
            {author_name},
            {user_id},
            {category},
            {blurb},
            {northanger},
            {sense},
            {pride},
            {emma},
            {mansfield},
            {persuasion},
            {juvenilia},
            {misc},
            {created_date},
            {last_update},
            NULL,
            {completed},
            NULL,
            {base_url},
            {sub_dir},
            0
        ");'''

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
            last_update = {last_update},
            completed = {completed},
        WHERE title_name == {title_name} AND author_name == {author_name};
        '''
        
#TODO: explain this operation:
def bad_sql_escape(text):
    return "'" + text.strip().replace("'", "''") + "'"

def generate_sql_statement(action, line):  

    # This is how sql escapes things
    blurb = bad_sql_escape(line[blurb_index])
    # New stories are not multipart
    #TODO - can I do a straightreplacement of sub_dir or is it a keyword?
    sub_dir = dwq_archive_dir

    #TODO: not tracking numChapters?

    #TODO: verify the various url fields, what does this line do and what is the field?
    if action == "ArchiveNew":
        base_url = os.path.splitext(os.path.basename(line[new_filename_index]))[0]

        '''
        #TODO: in this old code, what is the f? and how is this substitution supposed to work?
            is it some sort of implicit template??  It didn't seem to work for me...
        insert_sql = f"""
        INSERT INTO dwg_stories VALUES (
            {line[5]!r}, NULL, '/derby/2019/{line[16]}', {line[4]!r}, {line[3]}, {gen_type!r},
            {blurb},
            {genre_bools}, {line[1]!r}, {line[0]!r}, NULL, {completed}, {genera}, {base_url!r}, {sub_dir!r}, {multipart}
        );"""
        '''
        #TODO by not specifying the column names, we are assuming the correct order, safe?...
        sql_statement = SQL_INSERT_TEMPLATE.format(
            title_name = line[title_index],
            story_url = '/DWG_DIR/dwq_archive_dir/'+line[new_filename_index],
            author_name = line[author_index],
            user_id = line[author_id_index],
            category = line[category_index],
            blurb = blurb,
            northanger = line[northanger_index],
            sense = line[sense_index],
            pride = line[pride_index],
            emma = line[emma_index],
            mansfield = line[mansfield_index],
            persuasion = line[persuasion_index],
            juvenilia = line[juvenilia_index],
            misc = line[misc_index],
            created_date = line[creation_date_index],
            last_update = line[post_date_index],
            completed = line[final_post_index],
            base_url = base_url,
            sub_dir = dwq_archive_dir)
  
    elif action == "AppendArchive":
        # be very careful with this statement! WHERE must be precise so as to not overwrite all the entries!
        # We only specify the few columns that can change
        #   by definition, title_name, author_name don't change
        #   story_url can't change: 
        #TODO: does category column have a name? cause in theory, could change it
            #?? = line[category_index]!r},
        sql_statement = SQL_UPDATE_TEMPLATE.format(
            title_name = line[title_index],
            author_name = line[author_index],
            blurb = blurb,
            northanger = line[northanger_index],
            sense = line[sense_index],
            pride = line[pride_index],
            emma = line[emma_index],
            mansfield = line[mansfield_index],
            persuasion = line[persuasion_index],
            juvenilia = line[juvenilia_index],
            misc = line[misc_index],
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

new_filelist = ['Files to write to /'+dwq_archive_dir+' :']
archive_filelist = ['Files to overwrite: ']


with open(input_csv_filename) as csv_file:
    reader = csv.reader(csv_file)
    lines = list(reader)

header = lines.pop(0)
#print ("\n{} files to process: \n".format(len(lines)))

assert header == header_test, header

from collections import Counter
c = Counter()
with open(output_sql_filename, "w") as sql_file:
    for line in lines:
        action = line[action_index]
        c[action] += 1

        sql_statement = generate_sql_statement(action, line)
        #print (sql_statement)

        if action == "ArchiveNew":
            new_filelist.append(line[new_filename_index])

        elif action == "AppendArchive":
            archive_filelist.append(line[archive_url_index])

        else:
            print("Unexpected action", action, line)
            continue

    sql_file.write(sql_statement + "\n")

#TODO should we write these to a file?
print('ensure that these files get written to dwiggie_c: \n')
print(new_filelist)
print()
print(archive_filelist)
print('\nNumber of files to process: ')
print(c)
