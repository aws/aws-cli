**To get information about a specified instance snapshot**

The following ``get-instance-snapshot`` example displays details about the specified instance snapshot. ::

    aws lightsail get-instance-snapshot \
        --instance-snapshot-name MEAN-1-1571419854

Output::

    {
        "instanceSnapshot": {
            "name": "MEAN-1-1571419854",
            "arn": "arn:aws:lightsail:us-west-2:123456789012:InstanceSnapshot/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
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
            "fromInstanceArn": "arn:aws:lightsail:us-west-2:123456789012:Instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "fromBlueprintId": "mean",
            "fromBundleId": "medium_3_0",
            "isFromAutoSnapshot": false,
            "sizeInGb": 80
        }
    }

For more information, see `Snapshots in Amazon Lightsail <https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-snapshots-in-amazon-lightsail.html>`__ in the *Amazon Lightsail User Guide*.
