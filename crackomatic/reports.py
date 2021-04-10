from io import BytesIO
import collections
import enum
import json
import re

import matplotlib
# https://stackoverflow.com/a/29172195
matplotlib.use('Agg')
from matplotlib import pyplot as plt  # noqa

from .models import Report  # noqa


class QuantityType(enum.Enum):
    SCALAR = enum.auto()
    PERCENTAGE = enum.auto()
    DISTRIBUTION = enum.auto()
    RANKINGLIST = enum.auto()


meta_data = dict(
    cracked=dict(
        type=QuantityType.PERCENTAGE,
        title="Percentage of hashes cracked",
        description="""This chart shows you the percentage of how many hashes
were cracked. Lower is better.""",
    ),
    total_hashes=dict(
        type=QuantityType.SCALAR,
        title="Total hash count",
        description="""This number represents the total amount of hashes that
were subject of the audit.""",
    ),
    cliques=dict(
        type=QuantityType.DISTRIBUTION,
        title="Clique size distribution",
        description="""A "clique" is a collection of at least two accounts
that all have the same password. This chart visualizes the number of cliques
for each size. This is independent of the number of cracked accounts,
because accounts with the same password also have the same hash. Active
Directory does not use a salt to store passwords.""",
        xmin=2,
    ),
    largest_clique=dict(
        type=QuantityType.SCALAR,
        title="Size of largest clique",
        description="The largest clique consists of this many accounts.",
    ),
    cliquiness=dict(
        type=QuantityType.PERCENTAGE,
        title="Cliquiness",
        description="""The 'cliquiness' is a measure of how prevalent
password reuse is in this domain. A cliquiness of zero means all
passwords are unique. A cliquiness of 100% means every account uses the same
password. Lower is better.""",
    ),
    mean_pw_len=dict(
        type=QuantityType.SCALAR,
        title="Mean password length",
        description="""The geometric mean length of all passwords that were
cracked. Note that passwords that resisted the cracking attempt do not
influence this number.""",
    ),
    lengths=dict(
        type=QuantityType.DISTRIBUTION,
        title="Length distribution",
        description="""This histogram shows the number of cracked passwords
for each length.""",
    ),
    char_classes=dict(
        type=QuantityType.DISTRIBUTION,
        title="Character class count distribution",
        description="""Character classes are: upper letters, lower letters,
digits, special characters. This chart shows how many cracked passwords are
using any number of character classes.""",
    ),
    top_basewords=dict(
        type=QuantityType.RANKINGLIST,
        title="Top basewords",
        description="",
    ),
    top_patterns=dict(
        type=QuantityType.RANKINGLIST,
        title="Top patterns",
        description="""<ul><li>Abc1: Start with capital, end with one
        digit</li><li>Abc12: Start with capital, end with two digits
        </li><li>Abc123: Start with capital, end with three digits
        </li><li>Abc1234: Start with capital, end with four digits
        </li><li>Abcdef!: Start with capital, end with special character
        </li><li>abcdef: All lower case letters
        </li><li>123456: All digits
        </li><li>?: No known pattern</li></ul>
        """,
    ),
)


def create_report(passwords, hashes):
    if len(hashes):
        cracked = len(passwords)/len(hashes)
    else:
        cracked = 0

    if len(passwords):
        mean_pw_len = sum(map(len, passwords))/len(passwords)
    else:
        mean_pw_len = None

    lengths = collections.Counter(map(len, passwords))

    cliques = collections.Counter(hashes)
    # 0% means everybody has a unique password
    # 100% means everybody has the same password
    if len(hashes) == 1:
        cliquiness = None
    else:
        cliquiness = 1 - (len(cliques) - 1) / (len(hashes) - 1)
    try:
        largest_clique = cliques.most_common(1)[0][1]
    except IndexError:
        largest_clique = None
    cliques = collections.Counter(cliques.values())
    if 1 in cliques:
        del cliques[1]

    char_classes = get_char_classes(passwords)
    top_basewords = get_top_basewords(passwords)
    top_patterns = get_top_patterns(passwords)

    return Report(
        cracked=cracked,
        total_hashes=len(hashes),
        mean_pw_len=mean_pw_len,
        lengths=json.dumps(lengths),
        cliques=json.dumps(cliques),
        largest_clique=largest_clique,
        cliquiness=cliquiness,
        char_classes=json.dumps(char_classes),
        top_basewords=json.dumps(top_basewords),
        top_patterns=json.dumps(top_patterns),
    )


def create_text_report(report):
    result = ""
    for k, v in meta_data.items():
        value = get_text_represenation(report, k)
        if isinstance(value, dict):
            result += "%s:\n    " % v['title']
            result += "\n    ".join(["%s: %s" % (k, str(v)) for k, v in value])
        elif isinstance(value, list):
            result += "%s:\n    " % v['title']
            result += "\n    ".join(["%s: %s" % (k, str(v)) for k, v in value])
        else:
            result += "%s: %s\n" % (v['title'], value)

    return result


def get_text_represenation(report, quantity):
    val = getattr(report, quantity)
    if val is None:
        return 'Undefined'
    type = meta_data[quantity]['type']
    if type == QuantityType.PERCENTAGE:
        return '%.02f%%' % (val * 100)
    elif type == QuantityType.SCALAR and isinstance(val, float):
        return '%.02f' % val
    else:
        return str(val)


def get_html_representation(report, quantity):
    val = getattr(report, quantity)
    if val is None:
        return ''
    type = meta_data[quantity]['type']
    if type == QuantityType.PERCENTAGE:
        return gauge_chart(val)
    elif type == QuantityType.SCALAR:
        return number(val)
    elif type == QuantityType.DISTRIBUTION:
        if 'xmin' in meta_data[quantity]:
            xmin = meta_data[quantity]['xmin']
        else:
            xmin = 0
        return histogram(val, xmin)
    elif type == QuantityType.RANKINGLIST:
        return bar_chart(val)


def histogram(dct, xmin=0):
    dct = json.loads(dct)
    if not dct:
        return ""
    plt.rcdefaults()
    new_dct = {}
    for i in range(xmin, 1 + max(map(int, dct.keys()))):
        try:
            new_dct[i] = dct[str(i)]
        except KeyError:
            new_dct[i] = 0
    fig, ax = plt.subplots()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylabel('#')
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.bar(new_dct.keys(), new_dct.values(), tick_label=list(new_dct.keys()))
    svg = get_svg(plt)
    plt.close()
    return svg


def number(val):
    if isinstance(val, float):
        val = '%.02f' % val
    else:
        val = '%d' % val
    result = '<p class="scalar">%s</p>' % val
    return result


def get_top_patterns(passwords):
    patterns = {
        "Abc1": re.compile('^[A-Z].*[^0-9][0-9]$'),
        "Abc12": re.compile('^[A-Z].*[^0-9][0-9]{2}$'),
        "Abc123": re.compile('^[A-Z].*[^0-9][0-9]{3}$'),
        "Abc1234": re.compile('^[A-Z].*[^0-9][0-9]{4}$'),
        "Abcdef!": re.compile('^[A-Z].*[!.?,_/\\\\@"#$%^&*()+}{|-]$'),
        "abcdef": re.compile('^[a-z]*$'),
        "123456": re.compile('^[0-9]*$'),
    }
    counts = collections.Counter()
    for p in passwords:
        for k, v in patterns.items():
            if v.match(p):
                counts.update([k])
                break
        counts.update(["?"])
    return counts.most_common(10)


def get_char_classes(passwords):
    def get_character_classes(s):
        upper = False
        lower = False
        digits = False
        chars = False
        if re.search('[A-Z]', s):
            upper = True
        if re.search('[a-z]', s):
            lower = True
        if re.search('[0-9]', s):
            digits = True
        if re.search('[^A-Za-z0-9]', s):
            chars = True
        result = sum([upper, lower, digits, chars])
        return result

    counts = collections.Counter()
    for p in passwords:
        classes = get_character_classes(p)
        counts.update([classes])
    return counts


def get_top_basewords(passwords):
    counts = collections.Counter()
    for p in passwords:
        if not p:
            continue
        # Convert to lower case
        p = p.lower()

        # Remove special chars and digits from beginning and end
        p = re.sub('[0-9!@#$%^&*())_+~}|"? ><,./\\\'[\\]-]*$', '', p)
        p = re.sub('^[0-9!@#$%^&*())_+~}|" ?><,./\\\'[\\]-]*', '', p)

        # De-leet-ify
        p = p.replace('!', 'i')
        p = p.replace('1', 'i')
        p = p.replace('0', 'o')
        p = p.replace('3', 'e')
        p = p.replace('@', 'a')
        p = p.replace('+', 't')
        p = p.replace('$', 's')

        # Remove remaining special chars
        p = re.sub('[!@#$%^&*())_+~}|"?><,./\\\'[\\]-]', '', p)

        # Forget this if it's empty by now
        if not p:
            continue

        # Is it multiple words? Get the longest
        p = sorted(p.split(), key=len)[-1]

        # If there are digits left (i.e. it's not a word) or the word is
        # empty, we're not interested anymore
        if not re.search('[0-9]', p) and p:
            counts.update([p])

    # Remove basewords shorter than 3 characters or occurance less than 2
    for k in counts.copy():
        if counts[k] == 1 or len(k) < 3:
            del counts[k]
    return counts.most_common(10)


def create_figures(report):
    figures = []
    for k, v in meta_data.items():
        html = get_html_representation(report, k)
        figures.append(dict(
            html=html,
            title=v['title'],
            description=v['description'],
        ))
    return figures


def bar_chart(lst):
    """Takes a string that is json-convertable to a list of tuples"""
    lst = json.loads(lst)
    if not lst:
        return ""
    labels = [x[0] for x in lst]
    values = [x[1] for x in lst]
    plt.rcdefaults()
    fig, ax = plt.subplots(figsize=(8, len(labels)/2), dpi=100)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    y_pos = range(len(labels))
    ax.barh(y_pos, values, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('#')
    #  ax.set_title('')
    svg = get_svg(plt)
    plt.close()
    return svg


def gauge_chart(value):
    val = [1 - value, value, 1]
    colors = ['lightgray', 'tab:blue', 'k']
    plt.figure(figsize=(8, 6), dpi=100)

    wedges, labels = plt.pie(
        val,
        wedgeprops=dict(width=0.4, edgecolor='w'),
        colors=colors,
    )
    # Remove bottom half of the circle
    wedges[-1].set_visible(False)

    plt.text(
        0, 0.2,
        "%.01f%%" % (value*100),
        fontdict=dict(
            family='sans-serif',
            color='gray',
            weight='bold',
            size=28,
        ),
        horizontalalignment='center',
        verticalalignment='center',
    )

    svg = get_svg(plt, .2, .1, .63, .5)
    plt.close()
    return svg


def get_svg(plt, a1=0, a2=0, a3=1, a4=1):
    f = BytesIO()
    plt.savefig(f, format="svg")
    figdata = f.getvalue().decode()
    # Remove xml header and DTT
    figdata_svg = '<svg' + figdata.split('<svg')[1]
    m = re.search(
        'viewBox="([0-9.-]+) ([0-9.-]+) ([0-9.-]+) ([0-9.-]+)"',
        figdata_svg,
    )
    viewbox = tuple(map(float, m.groups()))
    new_viewbox = (
        viewbox[2]*a1,
        viewbox[3]*a2,
        viewbox[2]*a3,
        viewbox[3]*a4,
    )
    viewbox = "%d %d %d %d" % new_viewbox
    figdata_svg = re.sub('viewBox="[0-9. -]+"',
                         'viewBox="%s"' % viewbox,
                         figdata_svg)
    figdata_svg = re.sub('height="[0-9.]+pt"',
                         'height="100%"',
                         figdata_svg)
    figdata_svg = re.sub('width="[0-9.]+pt"',
                         'width="100%"',
                         figdata_svg)
    return figdata_svg
