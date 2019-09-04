# -*- coding: utf8 -*-
import csv
import os.path

OUTPUT_CSV_PATH="dwg_archive_results.csv"
OUTPUT_SQL_PATH="dwg_archive_results.sql"

headers_test = [
    'last_update/Posting', 'date_created', 'Msg Id', 'author_id', 'author_name',
    'title_name', 'action', 'category', 'new posting - real url', 'archive real url',
    'FinalPost?', 'Book', 'Blurb', 'Archive Title', 'Archive Title ID',
    'URL', '', 'New Filename'
]

headers_demo = [
    '2016-08-23', '2012-10-23', '', 'NULL', 'Abbie C.',
    'Fearful Symmetry', 'AppendArchive', 'epilogue', 'https://www.dwiggie.com/phorum/read.php?5,119384', 'https://www.dwiggie.com/derby/abbiecb.htm',
    'N', '', '', '', '',
    '/derby/abbiecb.htm', 'abbiecb.htm'
]

sql_schema =  """
  title_name varchar(255), title_id int(20) NOT NULL AUTO_INCREMENT,
  story_url varchar(255), author_name varchar(100)
  user_id int(10), type enum('Epi','Fant','ANI'),
  blurb text,
  northanger tinyint(1), sense tinyint(1), pride tinyint(1), emma tinyint(1),
  mansfield tinyint(1), persuasion tinyint(1), juvenilia tinyint(1), misc tinyint(1),
  created date, last_update date,
  num_chapters int(5), completed tinyint(1),
  genera varchar(255),
  base_url varchar(20), sub_dir varchar(30),
  multi_part tinyint(1),
  PRIMARY KEY (title_id)
"""

def bad_sql_escape(text):
    return "'" + text.strip().replace("'", "''") + "'"

def generate_insert(line):
    genre_types = {"epilogue": "Epi", "fantasia": "Fant"}
    # Epi Fant ANI
    assert line[7] in genre_types, line
    gen_type = genre_types[line[7]]

    # northanger, sense, pride, emma, mansfield, persuasion, juvenilia, misc
    genre_bool_lookup = {
        "NA":   "1, NULL, NULL, NULL, NULL, NULL, NULL, NULL",
        "S&S":  "NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL",
        "P&P":  "NULL, NULL, 1, NULL, NULL, NULL, NULL, NULL",
        "Em":   "NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL",
        "MP":   "NULL, NULL, NULL, NULL, 1, NULL, NULL, NULL",
        "Per":  "NULL, NULL, NULL, NULL, NULL, 1, NULL, NULL",
        "Misc": "NULL, NULL, NULL, NULL, NULL, NULL, NULL, 1",
    }
    assert line[11] in genre_bool_lookup, (line[11], line)
    genre_bools = genre_bool_lookup[line[11]]
    genera = "NULL"

    # This is how sql escapes things
    blurp = bad_sql_escape(line[12])

    completed = 0 if line[10].upper() == 'N' else 1

    base_url = os.path.splitext(os.path.basename(line[16]))[0]
    sub_dir = "2019"

    # New stories are not multipart
    multipart = 0

    insert_sql = f"""
INSERT INTO dwg_stories VALUES (
    {line[5]!r}, NULL, '/derby/2019/{line[16]}', {line[4]!r}, {line[3]}, {gen_type!r},
    {blurp},
    {genre_bools}, {line[1]!r}, {line[0]!r}, NULL, {completed}, {genera}, {base_url!r}, {sub_dir!r}, {multipart}
);"""
    return insert_sql



with open(OUTPUT_CSV_PATH) as csv_file:
    reader = csv.reader(csv_file)
    lines = list(reader)

headers = lines.pop(0)
print ("csv", len(lines))
assert headers == headers_test, headers

from collections import Counter
c = Counter()
with open(OUTPUT_SQL_PATH, "w") as sql_file:
    for line in lines:
        action = line[6]
        c[action] += 1

        if action == "ArchiveNew":
            insert_sql = generate_insert(line)
            #print (insert_sql)
            sql_file.write(insert_sql + "\n")

        elif action == "AppendArchive":
            #insert_sql = generate_insert(line)
            # Same thing but be careful
            print ("Skipping", action, line[14], "for now")
            pass

        elif action in ("dna", "delete"):
            print ("Skipping", action, line[14], "for now")
            #print (action)
            pass

        else:
            print(action)

print(c)
