#!/usr/bin/env python

import sys

import catmaid

server = 'http://catmaid.hms.harvard.edu/catmaid3/'
if len(sys.argv) > 1:
    server = sys.argv[1]

print "connecting to server: %s" % server
c = catmaid.connect(server)

print "api_token: %s" % c.api_token

projects = c.projects
print "projects: %s" % projects

for project in projects:
    pid = project.get('pid', project.get('id', -1))
    if pid == -1:
        continue
    print("Project[%s]: %s" % (pid, project['title']))
    c.set_project(pid)
    sids = c.skeleton_ids()
    print("\t%i skeletons" % len(sids))
    if len(sids):
        sid = sids[0]
        sk = c.skeleton(sid)
        print("\tskeleton[%s] type=%s" % (sid, type(sk)))
    wd = c.wiring_diagram()
    print("\tfetched wiring diagram")
