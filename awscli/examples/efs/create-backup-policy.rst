**To enable automatic backups for a file system**

The following ``put-backup-policy`` example shows how to enable automatic backups for an existing Amazon EFS file system by creating a backup policy.::

    aws efs put-backup-policy \
        --file-system-id fs-4gd2a78et \
        --backup-policy Status=ENABLED


Output::

    {
        "BackupPolicy": {
        "Status": "ENABLED"
        }
    }

This command sets the backup policy for the file system with the ID fs-4gd2a78et to enable automatic backups.

For more information, see `Amazon EFS Backup Policies <https://docs.aws.amazon.com/efs/latest/ug/awsbackup.html>`__ in the *Amazon Elastic File System User Guide.*.