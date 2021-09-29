**To view the status of a root volume replacement task**

The following ``describe-replace-root-volume-tasks`` example describes the specified root volume replacement task. ::

    aws ec2 describe-replace-root-volume-tasks \
        --replace-root-volume-task-ids replacevol-05efec875b94ae34d

Output::

    {
        "ReplaceRootVolumeTasks": [
            {
                "ReplaceRootVolumeTaskId": "replacevol-05efec875b94ae34d",
                "InstanceId": "i-1234567890abcdef0",
                "TaskState": "succeeded",
                "StartTime": "2021-09-16 02:19:30.0",
                "CompleteTime": "2021-09-16 02:19:56.0",
                "Tags": []
            }
        ]
    }

For more information, see `Replace an Amazon EBS volume <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-restoring-volume.html>`__ in the *Amazon EC2 User Guide*.