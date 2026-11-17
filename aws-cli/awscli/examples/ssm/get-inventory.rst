**To view your inventory**

The following ``get-inventory`` example gets the custom metadata for your inventory. ::

    aws ssm get-inventory

Output::

    {
        "Entities": [
            {
                "Data": {
                    "AWS:InstanceInformation": {
                        "Content": [
                            {
                                "ComputerName": "ip-172-31-44-222.us-west-2.compute.internal",
                                "InstanceId": "i-0cb2b964d3e14fd9f",
                                "IpAddress": "172.31.44.222",
                                "AgentType": "amazon-ssm-agent",
                                "ResourceType": "EC2Instance",
                                "AgentVersion": "2.0.672.0",
                                "PlatformVersion": "2016.09",
                                "PlatformName": "Amazon Linux AMI",
                                "PlatformType": "Linux"
                            }
                        ],
                        "TypeName": "AWS:InstanceInformation",
                        "SchemaVersion": "1.0",
                        "CaptureTime": "2017-02-20T18:03:58Z"
                    }
                },
                "Id": "i-0cb2b964d3e14fd9f"
            }
        ]
    }

For more information, see `AWS Systems Manager Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html>`__ in the *AWS Systems Manager User Guide*.
