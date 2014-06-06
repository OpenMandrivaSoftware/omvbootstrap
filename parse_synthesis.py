# -*- Mode: Python; coding: utf-8 -*-

##
## Copyright (C) 2010 Mandriva S.A. <http://www.mandriva.com>
## All rights reserved
##
## This program is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by the Free
## Software Foundation, either version 3 of the License, or any later version.
##
## This program is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
## FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
## more details.
##
## You should have received a copy of the GNU General Public License along with
## this program.  If not, see <http://www.gnu.org/licenses/>.
##
##   Contributor(s):    J. Victor Duarte Martins <jvictor@mandriva.com>
##
"""
A synthesis.hdlist.cz parser
"""

import gzip
import re
import sys

try:
    import lzma
except ImportError:
    from backports import lzma

__all__ = ['parse']

def _parse_rpm_name(name):
    """Returns (name, version, release, arch) tuple from a rpm
    package name.
    """

    # TODO This could be put in a package for general use in other
    # scripts.

    parts = name.split('-')
    release_arch = parts[-1].split('.')

    arch = release_arch[-1]
    dist = '.'.join(release_arch[:-1])
    release = parts[-2]

    version = parts[-3]
    name = '-'.join(parts[0:-3])

    return (name, version, release, dist, arch)

def _parse_rpm_capability_list(cap_str_list):
    """Parse a list of capabilities specifications strings and
    their restrictions.  Returns a list of dictionaries for each
    capability."""

    cap_list = []

    for cap_str in cap_str_list:
        m = re.match('^(?P<name>[^[]+)(?:\[\*])*(?P<restriction>\[.*])?',
                     cap_str)
        if m is None:
            continue    # ignore malformed names

        cap = {'name': m.group('name')}
        restriction = m.group('restriction')

        if restriction is not None:

            # TODO This will accept restrictions with only
            # conditions, or invalid conditions (like =, or >=<):
            r = re.match('\[(?P<condition>[<>=]*) *(?P<version>.*)]',
                         restriction)

            if r is not None:
                cap['restriction'] = {'condition': r.group('condition'),
                                      'version': r.group('version')}
        cap_list.append(cap)

    return tuple(cap_list)

def handleline(line, add_raw):
    pkg = {}
    
    if add_raw:
        if 'raw' not in pkg:
            pkg['raw'] = ''
        pkg['raw'] += line

    fields = line.rstrip('\n').split('@')[1:]
    ltype = fields.pop(0)

    if ltype == 'info':
        (pkg['name'],
         pkg['version'],
         pkg['release'],
         pkg['dist'],
         pkg['arch']) = _parse_rpm_name(fields.pop(0))
        for field in ('epoch', 'size', 'group'):
            pkg[field] = fields.pop(0)
        yield pkg
        pkg = {}
    elif ltype == 'summary':
        pkg['summary'] = fields.pop(0)
    elif ltype in ('requires', 'provides', 'conflict', 'obsoletes'):
        pkg[ltype] = _parse_rpm_capability_list(fields)

def parse(hdlist, add_raw=False):
    """Create a generator of packages parsed from synthesis hdlist
    file."""

    try:
        for line in gzip.open(hdlist, 'rb'):
            yield handleline(line, add_raw)
    except IOError:
        for line in lzma.open(hdlist, 'rb'):
            yield handleline(line, add_raw)

if __name__ == '__main__':
    hdlist = sys.argv[1]

    pkgs = sys.argv[2:]

    found = []

    metadata = []

    for p in parse(hdlist, True):
        metadata.append(p)

    # do half-assed backwards search
    for m in metadata:
        if m['name'] in pkgs:
            found.append(m)

    # check if we didn't get all the packages
    if len(pkgs) != len(found): # we've missed something
        missing = []
        for i in pkgs:
            ok = False
            for f in found:
                if f['name'] == i:
                    ok = True
                    break
            if ok == False:
                missing.append(i)
        print "could not find some packages in repo: " + ' '.join(missing)
        sys.exit(1)

    # we have all packages! now do basic dep resolution
    for pkg in found:
        if 'requires' in pkg:
            for c in pkg['requires']:
                lookingFor = c['name']
                # search through all packages
                satisfied = False
                for m in metadata:
                    if m['name'] == lookingFor:
                        if m not in found:
                            found.append(m)
                        satisfied = True
                        break
                    for prov in m['provides']:
                        if prov['name'] == lookingFor:
                            if m not in found:
                                found.append(m)
                            satisfied = True
                            break
                    if satisfied == True:
                        break
                if satisfied == False:
                    print "package %s requires unsatisfied dep %s" % (pkg['name'], lookingFor)
                    sys.exit(1)

    # yay okay let's print package lists and exit
    for pkg in found:
        #if pkg['epoch'] == '0':
            print "%s-%s-%s-%s.%s" % (pkg['name'],pkg['version'],pkg['release'],pkg['dist'],pkg['arch'])
        #else:
        #    print "%s-%s:%s-%s-%s.%s" % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['dist'],pkg['arch'])

#    for p in parse(hdlist, True):
#        print "-" * 70
#        print p['raw']
#        print ("name = %s\n"
#        "version = %s\n"
#        "release = %s\n"
#        "arch = %s\n"
#        "epoch = %s\n"
#        "size = %s (%sK)\n"
#        "group = %s\n"
#        "summary:\n"
#        "%s") % (p['name'], p['version'], p['release'], p['arch'],
#                 p['epoch'], p['size'], int(p['size']) / 1024.0, p['group'],
#                 p['summary'])
#
#        for cap in ('requires', 'provides', 'conflict', 'obsoletes'):
#            if cap in p:
#                print cap
#                for c in p[cap]:
#                    print "- name: %s" % c['name'],
#                    if 'restriction' in c:
#                        print "%s %s" % (c['restriction']['condition'],
#                                         c['restriction']['version']),
#                    print
        #raw_input()
