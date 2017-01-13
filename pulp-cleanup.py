#!/usr/bin/env python
import subprocess
import shutil
import shlex
import json
import glob
import os
"""
Workaround for Red Hat Bugzilla #1184442 & #1317057
===================================================
Early versions of Satellite (6.1.x) contained a bug where the content was saved to the wrong
location. After each un-used Content View is removed, the script will check if there is content
in the wrong location and move the data to a backup directory (in-case recovery is required).
If aforementioned files are not found, no action will be taken and script will continue to next
Content View.

Tasks:
- Delete content-view versions older than n-1 (keep previous version for rollback purposes)
- Move related Pulp yum content to a backup directory to be manually deleted at a later date

WARNING:
DO NOT RUN THIS SCRIPT IF YOU WANT TO KEEP CONTENT VERSIONS NOT CURRENTLY IN A LIFECYCLE!!!

Tested on Satellite 6.1.x -> 6.2.6
"""
__author__ = 'Blayne Campbell'
__date__ = '2016-07-06'

DEBUG = True

try:
    # try to load site specific settings from settings.json in local directory
    with open('settings.json', 'r') as f:
        settings = json.load(f)
except (IOError, ValueError):
    # if settings.json does not exist, gather information from user and save to file
    print("a valid settings.json was not found.")
    organization = raw_input("Provide an organization label: ")
    backup_directory = raw_input("Provide full path to backup location: ")
    settings = {"ORG_LABEL": organization, "BACKUP_DIR": backup_directory}
    with open('settings.json', 'w') as f:
        json.dump(settings, f)


# Content Organization Label:
ORG_LABEL = settings['ORG_LABEL']
# Pulp directory to clean:
PULP_DIR = '/var/lib/pulp/published/yum/master'
# Backup directory:
BACKUP_DIR = settings['BACKUP_DIR']


def all_content_views():
    command = 'hammer --output=json content-view list --organization-label %s' % ORG_LABEL
    result = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    result.wait()
    return json.loads(result.communicate()[0])


def old_content_versions(cv_id):
    command = 'hammer --output=json content-view version list --content-view-id %s' % cv_id
    result = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    result.wait()
    all_versions = json.loads(result.communicate()[0])
    unused_versions = [x for x in all_versions if not x['Lifecycle Environments']]
    sorted_unused_versions = [x for x in sorted(unused_versions, key=lambda x: x['ID'])]
    # Keep n-1 for rollback reasons
    if len(sorted_unused_versions) >= 2:
        protected_version = sorted_unused_versions[-1]
        print("protecting version: %s" % protected_version['Version'])
        sorted_unused_versions = sorted_unused_versions[:-1]
        return sorted_unused_versions


def delete_content_version(cv_version):
    command = 'hammer content-view version delete --id %s' % cv_version['ID']
    print('Deleting: %s' % cv_version['Name'])
    if not DEBUG:
        result = subprocess.Popen(shlex.split(command))
        result.wait()
        return result.returncode
        

def backup_content(cv_org, cv_label, cv_version):
    content_expression = '%s/%s-%s-%s_*' % (PULP_DIR, cv_org, cv_label, cv_version)
    related_content = glob.glob(content_expression)
    for content in related_content:
        if os.path.exists(content):
            print("Backup Source: %s" % content)
            print("Backup Destination: %s%s" % (BACKUP_DIR, content))
            if not DEBUG:
                shutil.move(content, "%s%s" % (BACKUP_DIR, content))
        else:
            # incremental versions will cause this condition.
            print("Skipping Backup (Source directory does not exist): %s" % content)

 
def main():
    all_views = all_content_views()
    content_views = [x for x in all_views if not x['Composite']]
    composite_views = [x for x in all_views if x['Composite']]
    print("\nCleaning unused 'Content' views..")
    for view in content_views:
        print("Processing: %s" % view['Label'])
        content_versions_to_remove = old_content_versions(view['Content View ID'])
        if not content_versions_to_remove:
            continue
        for version in content_versions_to_remove:
            delete_returncode = delete_content_version(version)
            if (delete_returncode == 0) or (DEBUG and delete_returncode == None):
                backup_content(ORG_LABEL, view['Label'], str(int(float(version['Version']))))
            else:
                print("Skipping content backup as content still in use.")
    print("\nCleaning unused 'Composite' views..")
    for view in composite_views:
        print("Processing: %s" % view['Label'])
        content_versions_to_remove = old_content_versions(view['Content View ID'])
        if not content_versions_to_remove:
            continue
        for version in content_versions_to_remove:
            delete_returncode = delete_content_version(version)
            if (delete_returncode == 0) or (DEBUG and delete_returncode == None):
                backup_content(ORG_LABEL, view['Label'], str(int(float(version['Version']))))
            else:
                print("Skipping content backup as content still in use.")


if __name__ == '__main__':
   main()
     
