import hashlib
import os
import time
import urllib.request

# 3rd party code you can comment or `pip install chardet`
import chardet



SLEEP_TIME = 2

# This is for the raw file data.
STORY_RAW = "stories_raw/"
# This is fo the file data converted to utf-8
STORY_DIRECTORY = "stories/"

DWG_FORUM_SCRIPT = ('<script type="text/javascript" src='
                    '"https://www.dwiggie.com/phorum/javascript.php?5">'
                    '</script>')


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

    page_data = raw_page_data.decode(encoding['encoding'])
    # Used when extracting forum posts, harmless in general
    page_data = page_data.replace(DWG_FORUM_SCRIPT, '')

    # Change file to be saved in utf-8 encoding.
    with open(cache_name, "w", encoding='utf-8') as cached:
        cached.write(page_data)

    return page_data

