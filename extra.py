# MOVE SOMEWHERE WHICH HAS GROUPINGS
def dad_results(groupings, processed):
    def hash_name(name):
        return STORY_DIRECTORY + processed[name]

    def link_for_name(name):
        return '<a href="{}">{}</a>'.format(hash_name(name), name)

    scores = []
    for k, v in groupings.items():
        fn = v[0]

        if not re.search(r'[0-9a]\.htm$', fn) and not re.search(r'/[a-z]*\.htm$', fn):
            continue

        with open(hash_name(fn)) as f:
            page_data = f.read().lower()

        length = len(page_data)

        darcies = page_data.count(' darcy')
        liz = page_data.count('liz')

        words = max(length / 10, page_data.count(' '))
        words = min(length / 4, words)

        d_score = math.sqrt(1000 * darcies / words)
        l_score = math.sqrt(1000 * liz / words)
        w_score = (words / 1000) ** 0.6

        scores.append((
            d_score + l_score + w_score,
            d_score, l_score, w_score,
            v))

    scores.sort(reverse = True)

    with open("dad_results.html", "w") as results:
        results.write('''
    <html>
    <body>
    <h1>Dad Meta JAFF Search</h1>
    <p>Searched {} stories to bring you these scores
    <hr>
    <table>
        <tr>
            <th>Overal "Score"</th>
            <th>Darcy's/1000 words</th>
            <th>Liz's/1000 words</th>
            <th>Length</th>

