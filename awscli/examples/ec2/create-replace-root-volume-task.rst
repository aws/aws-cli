**Example 1: To restore the root volume to its initial state**

The following ``create-replace-root-volume-task`` example restores the root volume of the specified instance to its initial state. ::

    aws ec2 create-replace-root-volume-task \
        --instance-id i-1234567890abcdef0

Output::

    {
        "ReplaceRootVolumeTask": {
            "ReplaceRootVolumeTaskId": "replacevol-05efec875b94ae34d",
            "InstanceId": "i-1234567890abcdef0
            "TaskState": "pending",
            "StartTime": "2021-09-16T00:19:30Z",
            "Tags": []
        }
    }

For more information, see `Replace an Amazon EBS volume <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-restoring-volume.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To restore the root volume to a specific snapshot**

The following ``create-replace-root-volume-task`` example replaces the root volume of the specified instance with the specified snapshot. ::

    aws ec2 create-replace-root-volume-task \
        --instance-id i-1234567890abcdef0 \
        --snapshot-id snap-9876543210abcdef0

Output::

    {
        "ReplaceRootVolumeTask": {
            "ReplaceRootVolumeTaskId": "replacevol-05efec875b94ae34d",
            "InstanceId": "i-1234567890abcdef0
            "TaskState": "pending",
            "StartTime": "2021-09-16T00:19:30Z",
            "Tags": []
        }
    }

For more information, see `Replace an Amazon EBS volume <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-restoring-volume.html>`__ in the *Amazon EC2 User Guide*.