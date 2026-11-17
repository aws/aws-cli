**To export an instance**

The following ``create-instance-export-task`` example creates a task to export the instance i-1234567890abcdef0 to the Amazon S3 bucket
myexportbucket. ::

    aws ec2 create-instance-export-task \
        --description "RHEL5 instance" \
        --instance-id i-1234567890abcdef0 \
        --target-environment vmware \
        --export-to-s3-task DiskImageFormat=vmdk,ContainerFormat=ova,S3Bucket=myexportbucket,S3Prefix=RHEL5

Output::

    {
        "ExportTask": {
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
    }

For more information, see `Export an EC2 instance as a VM using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport.html>`__ in the *VM Import/Export User Guide*.
