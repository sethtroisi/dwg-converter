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
            <th>link(s)</th>
        </tr>
    '''.format(len(scores)))

        for s, d,l,w, fns in scores[:50]:

            columns = [
                "{:.2f}".format(s),
                int(d**2),
                int(l**2),
                int(w**(1 / 0.6) * 1000),
                ",".join(link_for_name(fn) for fn in fns),
            ]

            row = "<tr>{}</tr>"
            values = "  <td>{}</td>"
            results.write(row.format("\n".join([values.format(v) for v in columns])))

        results.write('''
    </table>
    </body>
    </html>''')



'''
groupings_b = {}
for name in processed:
    #name = name.replace('https://www.dwiggie.com/', '')

    # path (e.g /old_2007/) matters
    path = os.path.dirname(name)
    title = os.path.basename(name)

    match = re.match('([a-z]+[0-9]*)([a-z]*).htm', title)
    if not match:
        # About 20 files like ann1_2.htm, laura8-9.htm
        print_weird(name)
        continue

    assert title.endswith('.htm'), (name, processed[name])
    title, part = match.groups()
    if len(part) > 1:
        print_weird(title)
        continue

    key = path + '/' + title + '.htm'
    if key not in groupings_b:
        groupings_b[key] = []
    groupings_b[key].append(name)

for k in groupings_b:
    groupings_b[k].sort()

print_grouping_info(groupings_b)
print()

def shorten(l):
    return [a.replace(DWIGGIE_PREFIX, "DWG/") for a in l]

for k in sorted(set(groupings.keys()) | set(groupings_b.keys())):
    a = groupings.get(k, [])
    b = groupings_b.get(k, [])
    if a != b:
        print_weird("Mismatch ({:30}):".format(k), shorten(a), shorten(b))
'''


