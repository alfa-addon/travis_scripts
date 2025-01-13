#!/usr/bin/env python
# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: romanvm@yandex.ua
# License: GPL v.3 <http://www.gnu.org/licenses/gpl-3.0.en.html>
"""
Deploy Kodi addons to GitHub repository and/or publish Sphinx docs to GitHub Pages
"""

from __future__ import print_function
import os
import sys
import shutil
import argparse
from subprocess import call
from xml.etree.ElementTree import ElementTree as ET

USER_NAME = os.environ.get('GIT_USER_NAME', 'Alfa')
USER_EMAIL = os.environ.get('GIT_USER_EMAIL', 'alfa-add-on@users.noreply.github.com')
DEVNULL = open(os.devnull, 'w')
GH_TOKEN = os.environ.get('GH_TOKEN', '')
PYV = sys.version_info[0]


# Utility functions
def execute(args, silent=False):
    if silent:
        stdout, stderr = DEVNULL, DEVNULL
    else:
        stdout, stderr = sys.stdout, sys.stderr

    call_string = ' '.join(args).replace(GH_TOKEN, '*****')
    print('Executing: ' + call_string)
    res = call(args, stdout=stdout, stderr=stderr)

    if res:
        raise RuntimeError('Call {call} returned error code {res}'.format(
            call=call_string,
            res=res
        ))


def clean_pyc(folder):
    cwd = os.getcwd()
    os.chdir(folder)
    paths = os.listdir(folder)

    for path in paths:
        abs_path = os.path.abspath(path)
        if os.path.isdir(abs_path):
            clean_pyc(abs_path)
        elif path[-4:] == '.pyc':
            os.remove(abs_path)
    os.chdir(cwd)


def create_zip(zip_name, root_dir, addon):
    clean_pyc(os.path.join(root_dir, addon))
    shutil.make_archive(zip_name, 'zip', root_dir=root_dir, base_dir=addon)
    print('ZIP created successfully.')


# Argument parsing
parser = argparse.ArgumentParser(description='Deploy an addon to my Kodi repo and/or publish docs on GitHub Pages')
parser.add_argument('-r', '--repo', help='push to my Kodi repo', action='store_true')
parser.add_argument('-d', '--docs', help='publish docs to GH pages', action='store_true')
parser.add_argument('-z', '--zip', help='pack addon into a ZIP file', action='store_true')
parser.add_argument('addon', nargs='?', help='addon ID', action='store', default='')
parser.add_argument('-k', '--kodi', nargs=1, help='the name of Kodi addon repo')
parser.add_argument('-b', '--branch', nargs=1, help='the name of a branch in the Kodi addon repo', default='krypton')
parser.add_argument('-v', '--version', nargs='?', help='writes the addon version [as read from xml] to the specified file (defaults to "version")', default='version')
args = parser.parse_args()

# Define args
if not args.addon:
    addon = os.environ.get('ADDON', 'plugin.video.alfa')
else:
    addon = args.addon

if not args.version:
    args.version = 'version'

# Define auxiliary variables
username = os.environ.get('GITHUB_REPOSITORY', 'alfa-addon/addon').split("/")[0]
repo_name = os.environ.get('ADDON_REPOSITORY', 'alfa-repo')
repo_slug = "{}/{}".format(username, repo_name)

# Define paths
root_dir = os.path.dirname(os.path.abspath(__file__))
kodi_repo_dir = os.path.join(root_dir, repo_name)
addon_dir = os.path.join(root_dir, addon)
docs_dir = os.path.join(root_dir, 'docs')
html_dir = os.path.join(docs_dir, '_build', 'html')

# Get add-on version from XML
xml = ET().parse(os.path.join(root_dir, addon, 'addon.xml'))
version = xml.get("version")

# Define ZIP locations
zip_name = '{0}-{1}'.format(addon, version)
zip_path = os.path.join(root_dir, zip_name + '.zip')

# Define URLs
REPO_URL_MASK = 'https://{username}:{gh_token}@github.com/{repo_slug}.git'
gh_repo_url = REPO_URL_MASK.format(username=username.lower(), gh_token=GH_TOKEN, repo_slug=repo_slug)
kodi_repo_url = REPO_URL_MASK.format(username=username.lower(), gh_token=GH_TOKEN, repo_slug=repo_slug)

# Start working
os.chdir(root_dir)

if args.version:
    _path = os.path.join(root_dir, args.version)
    with open(_path, "w") as file:
        file.write(version)

if args.zip:
    create_zip(zip_name, root_dir, addon)

if args.repo:
    if not os.path.exists(zip_path):
        create_zip(zip_name, root_dir, addon)

    if not os.path.exists(kodi_repo_dir) or \
       not os.path.exists(os.path.join(kodi_repo_dir, '.git')):
        execute(['git', 'clone', kodi_repo_url])

    os.chdir(kodi_repo_dir)
    execute(['git', 'remote', 'set-url', 'origin', kodi_repo_url])
    addon_repo = os.path.join(kodi_repo_dir, addon)

    if not os.path.exists(addon_repo):
        os.mkdir(addon_repo)

    shutil.copy(zip_path, addon_repo)
    shutil.copy(os.path.join(addon_dir, 'addon.xml'), addon_repo)
    os.chdir(kodi_repo_dir)
    execute(['sh', 'gen_repo.sh'])
    execute(['git', 'add', '--all', '.'])
    execute(['git', 'commit', '-m', 'Updated {addon} to v{version}'.format(addon=addon, version=version)])
    execute(['git', 'push', '--force'])

    print('Add-on {addon} v{version} deployed to Kodi repo'.format(addon=addon, version=version))

if args.docs:
    os.chdir(docs_dir)
    execute(['make', 'html'])
    os.chdir(html_dir)
    execute(['git', 'init'])
    execute(['git', 'config', 'user.name', USER_NAME])
    execute(['git', 'config', 'user.email', USER_EMAIL])
    open('.nojekyll', 'w').close()
    execute(['git', 'add', '--all', '.'])
    execute(['git', 'commit', '-m' 'Update {addon} docs to v.{version}'.format(addon=addon, version=version)])
    execute(['git', 'push', '--force', '--quiet', gh_repo_url, 'HEAD:gh-pages'], silent=True)
    print('{addon} docs v.{version} published to GitHub Pages.'.format(addon=addon, version=version))

if args.kodi:
    repo = args.kodi[0]
    branch = args.branch[0]
    os.chdir(root_dir)
    off_repo_fork = REPO_URL_MASK.format(gh_token=GH_TOKEN, repo_slug='alfa-addon/' + repo)
    execute(['git', 'clone', off_repo_fork], silent=True)
    os.chdir(repo)
    execute(['git', 'config', 'user.name', USER_NAME])
    execute(['git', 'config', 'user.email', USER_EMAIL])
    # execute(['git', 'remote', 'add', 'upstream', 'https://github.com/xbmc/{}.git'.format(repo)])
    execute(['git', 'fetch', 'upstream'])
    execute(['git', 'checkout', '-b', branch, '--track', 'origin/{}'.format(branch)])
    execute(['git', 'merge', 'upstream/{}'.format(branch)])
    os.system('git branch -D ' + addon)
    execute(['git', 'checkout', '-b', addon])
    clean_pyc(os.path.join(root_dir, addon))
    shutil.rmtree(os.path.join(root_dir, repo, addon), ignore_errors=True)
    shutil.copytree(os.path.join(root_dir, addon), os.path.join(root_dir, repo, addon))
    execute(['git', 'add', '--all', '.'])
    execute(['git', 'commit', '-m', '"[{addon}] {version}"'.format(addon=addon, version=version)])
    execute(['git', 'push', '--force', '--quiet', 'origin', addon])
