## pulp-cleanup 
_(Workaround for Red Hat internal Bugzilla #1184442 & #1317057 for Satellite 6.1.x)_  
**_Note: This is not an official solution. You should probably contact Red Hat support first._**

The aforementioned bugs result in content not being removed from disk when content versions
are deleted via the web GUI. Although there are a few content directories related to the bug, 
the majority of the disk space can be recovered by only removing the yum content associated 
with the deleted versions.

Usage:
- Modify `ORG_LABEL` and `BACKUP_DIR` to suit your implementation
- The script should be safe to execute with `DEBUG = True`. 
- Carefully review the stdout *before* disabling `DEBUG`.

Scripted Tasks:
- Delete 'content' view versions older than n-1 (keep previous version for rollback purposes)
- Delete 'composite' view versions older than n-1 (keep previous version for rollback purposes)
- Move related pulp yum content to a backup directory to be manually deleted at a later date

**WARNING:**  
**All versions NOT associated with a lifecycle will be removed with the exception of one previous version.**
