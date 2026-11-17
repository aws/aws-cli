**To view details about Dedicated Hosts**

The following ``describe-hosts`` example displays details for the ``available`` Dedicated Hosts in your AWS account. ::

    aws ec2 describe-hosts \
        --filter "Name=state,Values=available"

Output::

    {
        "Hosts": [
            {
                "HostId": "h-07879acf49EXAMPLE",
                "Tags": [
                    {
                        "Value": "production",
                        "Key": "purpose"
                    }
                ],
                "HostProperties": {
                    "Cores": 48,
                    "TotalVCpus": 96,
                    "InstanceType": "m5.large",
                    "Sockets": 2
                },
                "Instances": [],
                "State": "available",
                "AvailabilityZone": "us-west-2a",
                "AvailableCapacity": {
                    "AvailableInstanceCapacity": [
                        {
                            "AvailableCapacity": 48,
                            "InstanceType": "m5.large",
                            "TotalCapacity": 48
                        }
                    ],
                    "AvailableVCpus": 96
                },
                "HostRecovery": "on",
                "AllocationTime": "2019-08-19T08:57:44.000Z",
                "AutoPlacement": "off"
            }
        ]
    }

For more information, see `Monitor the state of your Amazon EC2 Dedicated Hosts <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-monitoring.html>`__ in the *Amazon EC2 User Guide*.
