**To get the CloudFormation stack records and their associated stacks**

The following ``get-cloud-formation-stack-records`` example displays details about the CloudFormation stack records and their associated stacks used to create Amazon EC2 resources from exported Amazon Lightsail snapshots. ::

    aws lightsail get-cloud-formation-stack-records

Output::

    {
        "cloudFormationStackRecords": [
            {
                "name": "CloudFormationStackRecord-588a4243-e2d1-490d-8200-3a7513ecebdf",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:CloudFormationStackRecord/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "createdAt": 1565301666.586,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "CloudFormationStackRecord",
                "state": "Succeeded",
                "sourceInfo": [
                    {
                        "resourceType": "ExportSnapshotRecord",
                        "name": "ExportSnapshotRecord-e02f23d7-0453-4aa9-9c95-91aa01a141dd",
                        "arn": "arn:aws:lightsail:us-west-2:123456789012:ExportSnapshotRecord/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                    }
                ],
                "destinationInfo": {
                    "id": "arn:aws:cloudformation:us-west-2:123456789012:stack/Lightsail-Stack-588a4243-e2d1-490d-8200-3EXAMPLEebdf/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                    "service": "Aws::CloudFormation::Stack"
                }
            }
        ]
    }

For more information, see `View CloudFormation stacks for Lightsail instances <https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-cloudformation-stacks.html>`__ in the *Amazon Lightsail User Guide*.
