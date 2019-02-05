import hashlib
import os
import time
import urllib.request

# 3rd party code you can comment or `pip install chardet`
import chardet


# Stories ({map of url to filename},
URL_DATA_PATH= 'url_data.json'


SLEEP_TIME = 2

# This is for the raw file data.
STORY_RAW = "stories_raw/"
# This is fo the file data converted to utf-8
STORY_DIRECTORY = "stories/"

DWG_FORUM_SCRIPT = ('<script type="text/javascript" src='
                    '"https://www.dwiggie.com/phorum/javascript.php?5">'
                    '</script>')


PRINT_COUNT = 0
def print_weird(*objects, **kwargs):
    global PRINT_COUNT
    PRINT_COUNT += 1
    print("(", PRINT_COUNT, ") ", sep="", end="")
    print(*objects, **kwargs)
    print()


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()


def get_raw_file(cached_filename, url=None):
    # this finds, caches, and opens a copy of a remote file

    # Check if we already downloaded & saved locally
    cache_name = STORY_RAW + cached_filename
    if os.path.exists(cache_name):
        with open(cache_name, "rb") as cached:
            page_data = cached.read()
        return page_data

    if not url:
        assert False, 'NO URL PROVIDED: ' + cached_filename

    print('Downloading "{}" => "{}"'.format(url, cached_filename))
    assert url.startswith("https:"), url

    request = urllib.request.urlopen(url)
    page_data = request.read()

    charset = request.info().get_content_charset()
    assert charset is None, ("DWG never provides this", url)

    with open(cache_name, "wb") as cached:
       cached.write(page_data)

    time.sleep(SLEEP_TIME)
    return page_data

def get_file(cached_filename, url=None):
    # this finds, caches, and opens a copy of a remote file

    cache_name = STORY_DIRECTORY + cached_filename
    if os.path.exists(cache_name):
        with open(cache_name, "r", encoding='utf-8') as cached:
            page_data = cached.read()
        return page_data

    raw_page_data = get_raw_file(cached_filename, url)
    encoding = chardet.detect(raw_page_data)
    encoding.pop('language') # not used
    print ("\tEncoding guess: {}".format(encoding))

    if encoding['encoding'] == 'Windows-1254':
        encoding['encoding'] = 'mac_iceland'
        print ("\tOVERRIDING SETTING:", encoding['encoding'])

    # Figure out where to store encodings.

    try:
        page_data = raw_page_data.decode(encoding['encoding'])
    except UnicodeDecodeError as e:
        # Could attemp something here
        test = [a for a in str(e).replace(':', '').split() if a.isnumeric()]
        test = int(test[0])
        print (test, raw_page_data[test - 15: test + 5])
        raise e

    # Used when extracting forum posts, harmless in general
    page_data = page_data.replace(DWG_FORUM_SCRIPT, '')

    # Change file to be saved in utf-8 encoding.
    with open(cache_name, "w", encoding='utf-8') as cached:
        cached.write(page_data)

    return page_data


def scan_raw():
    # Used to calculate and display all guesses
    from collections import Counter, defaultdict
    import tqdm

    counts = defaultdict(Counter)
    for i, fn in enumerate(tqdm.tqdm(os.listdir(STORY_RAW))):
        with open(os.path.join(STORY_RAW, fn), 'rb') as f:
            data = f.read()
        guess = chardet.detect(data)
        counts[guess['encoding']][round(guess['confidence'],3)] += 1
        if i % 100 == 0:
            print(counts)

    for encoding, count in sorted(counts.items()):
        print (encoding)
        for value, c in count.most_common(10):
            print("\t{} x confidence: {:.3f}".format(c, value))
        print()

    """
CP949
	1 x confidence: 0.990

ISO-8859-1
	1904 x confidence: 0.730
	2 x confidence: 0.725
	2 x confidence: 0.727
	2 x confidence: 0.728
	2 x confidence: 0.729
	1 x confidence: 0.723

Windows-1252
	1750 x confidence: 0.730
	6 x confidence: 0.729
	1 x confidence: 0.720
	1 x confidence: 0.727
	1 x confidence: 0.724

Windows-1254
	2 x confidence: 0.591
	1 x confidence: 0.589
	1 x confidence: 0.580
	1 x confidence: 0.595
	1 x confidence: 0.606
	1 x confidence: 0.582
	1 x confidence: 0.585

ascii
	1742 x confidence: 1.000

utf-8
	16 x confidence: 0.990
	3 x confidence: 0.876
	2 x confidence: 0.752
	1 x confidence: 0.938
"""

# texts = [b'vis-\x88-vis', b't\x90te-\x88', b'Bl\x81thne B\x94sendor']
# chars = u' \u00EA \u00E0 \u00FC \u00F6 '
# encodings = ['ascii', 'cp037', 'cp273', 'cp424', 'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857', 'cp858',      'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866', 'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026',     'cp1125', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258', 'cp65001', 'latin_1', 'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6', 'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13', 'iso8859_14', 'iso8859_15', 'iso8859_16', 'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154', 'utf_7', 'utf_8', 'utf_8_sig']
