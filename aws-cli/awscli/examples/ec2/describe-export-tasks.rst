**To list details about an instance export task**

The following ``describe-export-tasks`` example describes the export task with ID export-i-fh8sjjsq. ::

    aws ec2 describe-export-tasks \
        --export-task-ids export-i-fh8sjjsq

Output::

    {
        "ExportTasks": [
            {
                "State": "active",
                "InstanceExportDetails": {
                    "InstanceId": "i-1234567890abcdef0",
                    "TargetEnvironment": "vmware"
                },
                "ExportToS3Task": {
                    "S3Bucket": "myexportbucket",
                    "S3Key": "RHEL5export-i-fh8sjjsq.ova",
                    "DiskImageFormat": "vmdk",
                    "ContainerFormat": "ova"
                },
                "Description": "RHEL5 instance",
                "ExportTaskId": "export-i-fh8sjjsq"
            }
        ]
    }

For more information, see `Export an EC2 instance as a VM using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport.html>`__ in the *VM Import/Export User Guide*.
