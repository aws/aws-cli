**To get information about all of your instance snapshots**

The following ``get-instance-snapshots`` example displays details about all of the instance snapshots in the configured AWS Region. ::

    aws lightsail get-instance-snapshots

Output::

    {
        "instanceSnapshots": [
            {
                "name": "MEAN-1-1571421498",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:InstanceSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "supportCode": "6EXAMPLE3362/ami-0EXAMPLEe33cabfa1",
                "createdAt": 1571421527.755,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "InstanceSnapshot",
                "tags": [
                    {
                        "key": "no_delete"
                    }
                ],
                "state": "available",
                "fromAttachedDisks": [],
                "fromInstanceName": "MEAN-1",
                "fromInstanceArn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "fromBlueprintId": "wordpress",
                "fromBundleId": "micro_3_0",
                "isFromAutoSnapshot": false,
                "sizeInGb": 40
            },
            {
                "name": "MEAN-1-1571419854",
                "arn": "arn:aws:lightsail:us-west-2:123456789012:InstanceSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "supportCode": "6EXAMPLE3362/ami-0EXAMPLE67a73020d",
                "createdAt": 1571419891.927,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "resourceType": "InstanceSnapshot",
                "tags": [],
                "state": "available",
                "fromAttachedDisks": [],
                "fromInstanceName": "MEAN-1",
                "fromInstanceArn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "fromBlueprintId": "mean",
                "fromBundleId": "medium_3_0",
                "isFromAutoSnapshot": false,
                "sizeInGb": 80
            }
        ]
    }

For more information, see `Snapshots in Amazon Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
