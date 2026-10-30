**Example 1: To describe the status of a single volume**

The following ``describe-volume-status`` example describes the status for the volume ``vol-1234567890abcdef0``. ::

    aws ec2 describe-volume-status \
        --volume-ids vol-1234567890abcdef0

Output::

    {
        "VolumeStatuses": [
            {
                "VolumeStatus": {
                    "Status": "ok",
                    "Details": [
                        {
                            "Status": "passed",
                            "Name": "io-enabled"
                        },
                        {
                            "Status": "not-applicable",
                            "Name": "io-performance"
                        }
                    ]
                },
                "AvailabilityZone": "us-west-2a",
                "VolumeId": "vol-1234567890abcdef0",
                "Actions": [],
                "Events": []
            }
        ]
    }

For more information, see `Amazon EBS volume status checks <https://docs.aws.amazon.com/ebs/latest/userguide/monitoring-volume-checks.html>`__ in the *Amazon EBS User Guide*.

**Example 2: To describe the status of impaired volumes**

The following ``describe-volume-status`` example describes the status for all volumes that are impaired. In this example output, there are no impaired volumes. ::

    aws ec2 describe-volume-status \
        --filters Name=volume-status.status,Values=impaired

Output::

    {
        "VolumeStatuses": []
    }

For more information, see `Work with an impaired Amazon EBS volume <https://docs.aws.amazon.com/ebs/latest/userguide/work_volumes_impaired.html>`__ in the *Amazon EBS User Guide*.
