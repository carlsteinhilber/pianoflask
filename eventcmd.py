#!/usr/bin/env python

# a python-based pianobar event handler for future use

import os
import sys
from os.path import expanduser, join

path = os.environ.get('XDG_CONFIG_HOME')
if not path:
    path = expanduser("~/.config")
else:
    path = expanduser(path)
fn = join(path, 'pianobar', 'nowplaying_test')

info = sys.stdin.readlines()
cmd = sys.argv[1]

if cmd == 'songstart':
    with open(fn, 'w') as f:
        f.write("".join(info))