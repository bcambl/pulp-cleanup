#!/usr/bin/env python
import subprocess
import shutil
import shlex
import json
import glob
import os
"""
Workaround for Red Hat Bugzilla #1184442 & #1317057
==================================================
Please review README.md prior to use.
"""
__author__ = 'Blayne Campbell'
__date__ = '2016-07-06'

DEBUG = True

# Content Organization Label:
ORG_LABEL = 'Acme_Corporation'
# Pulp directory to clean (default location):
PULP_DIR = '/var/lib/pulp/published/yum/master'
# Backup directory:
BACKUP_DIR = '/pulp_backup'


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
        result = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
        result.wait()
        

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
            delete_content_version(version)
            backup_content(ORG_LABEL, view['Label'], str(int(float(version['Version']))))
    print("\nCleaning unused 'Composite' views..")
    for view in composite_views:
        print("Processing: %s" % view['Label'])
        content_versions_to_remove = old_content_versions(view['Content View ID'])
        if not content_versions_to_remove:
            continue
        for version in content_versions_to_remove:
            delete_content_version(version)
            backup_content(ORG_LABEL, view['Label'], str(int(float(version['Version']))))

if __name__ == '__main__':
   main()
     
