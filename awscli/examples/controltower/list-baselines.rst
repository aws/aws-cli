**To List Control Tower Baselines**

The following ``list-baselines`` example lists all available AWS Control Tower baselines::

    aws controltower list-baselines

Output::

    {
        "baselines": [
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/4T4HA1KMO10S6311",
                "description": "Sets up resources to monitor security and compliance of accounts in your organization.",
                "name": "AuditBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/J8HX46AHS5MIKQPD",
                "description": "Sets up a central repository for logs of API activities and resource configurations from accounts in your organization.",
                "name": "LogArchiveBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/LN25R72TTG6IGPTQ",
                "description": "Sets up shared resources for AWS Identity Center, which prepares the AWSControlTowerBaseline to set up Identity Center access for accounts.",
                "name": "IdentityCenterBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/17BSJV3IGJ2QSGA2",
                "description": "Sets up resources and mandatory controls for member accounts within the target OU, required for AWS Control Tower governance.",
                "name": "AWSControlTowerBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/3WPD0NA6TJ9AOMU2",
                "description": "Sets up a central AWS Backup vault in your organization.",
                "name": "BackupCentralVaultBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/H6C5JFCJJ3CPU3J5",
                "description": "Sets up AWS Backup Audit Manager.",
                "name": "BackupAdminBaseline"
            },
            {
                "arn": "arn:aws:controltower:us-east-1::baseline/APO9ATVPBKFRRGLK",
                "description": "Sets up a local AWS Backup vault and attaches multiple AWS Backup plans.",
                "name": "BackupBaseline"
            }
        ]
    }

For more information, see `AWS Control Tower Baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.