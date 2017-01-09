#!/usr/bin/env python

import json
import sys

import pylab


try:
    import catmaid
    has_catmaid = True
except ImportError:
    has_catmaid = False


def load_user_stats(source):
    if isinstance(source, (str, unicode)):
        with open(source, 'r') as f:
            d = json.load(f)
        return d['stats_table']
    elif has_catmaid and isinstance(source, catmaid.connection.Connection):
        return source.user_stats()['stats_table']
    raise Exception("Unknown source: {}".format(source))

fn = 'stats-user-history.json'


def cull_inactive(st, inactive=None):
    if inactive is None:
        inactive = []
    for u in st:
        active = False
        for d in st[u]:
            if len(st[u][d]):
                active = True
                break
        if not active:
            inactive.append(u)

    for u in inactive:
        del st[u]
    return st


def calculate_actions(st):
    for u in st:
        for d in st[u]:
            n = 0
            for a in st[u][d]:
                if a == 'actions':
                    continue
                n += st[u][d][a]
            st[u][d]['actions'] = n
    return st


def get_actions(st):
    actions = {}
    for u in st:
        for d in st[u]:
            for a in st[u][d]:
                actions[a] = 1
    return sorted(actions.keys())


def get_days(st):
    days = {}
    for u in st:
        for d in st[u]:
            days[d] = 1
    return sorted(days.keys())


def get_users(st):
    return sorted(st.keys())


global selected
selected = {}


def show_legend():
    ax = pylab.gca()
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # Put a legend to the right of the current axis
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))


def on_pick(event):
    global selected
    if len(selected):
        selected['label'].remove()
        selected['artist'].set_lw(selected['linewidth'])
        selected = {}
    label = pylab.text(
        event.mouseevent.xdata, event.mouseevent.ydata,
        event.artist.get_label())
    selected['label'] = label
    selected['artist'] = event.artist
    selected['linewidth'] = event.artist.get_lw()
    event.artist.set_lw(5)
    event.canvas.draw()


def keypress(event):
    if event.key == 'q':
        sys.exit()


def plot_user_stats(source, show=False):
    st = load_user_stats(source)
    st = cull_inactive(st)
    st = calculate_actions(st)
    # get average number of actions per day
    actions = get_actions(st)
    days = get_days(st)
    users = get_users(st)
    for action in actions:
        pylab.figure()
        actions_per_day = []
        for d in days:
            dt = 0
            n = 0.
            for u in st:
                dt += st[u][d].get(action, 0)
                n += 1.
            actions_per_day = dt / n

        pylab.plot(actions_per_day, linewidth=5, label='average', picker=5)
        for u in users:
            y = [st[u][d].get(action, 0) for d in days]
            pylab.plot(y, alpha=0.5, label=u, picker=5)
        pylab.title('{}'.format(action))
        show_legend()
        pylab.xticks(pylab.arange(len(days)), days, rotation=90)
        pylab.gcf().canvas.mpl_connect('pick_event', on_pick)
        pylab.gcf().canvas.mpl_connect('key_press_event', keypress)

    if show:
        pylab.show()


if __name__ == '__main__':
    #server, username, password, project = sys.argv[1:5]
    #c = catmaid.Connection(server, username, password, project=project)
    c = catmaid.connect()
    plot_user_stats(c, show=True)
