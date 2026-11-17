**To create an instance from a snapshot**

The following ``create-instances-from-snapshot`` example creates an instance from the specified instance snapshot, in the specified AWS Region and Availability Zone, using the $12 USD bundle.

**Note:** The bundle that you specify must be equal to or greater in specifications than the bundle of the original source instance used to create the snapshot. ::

    aws lightsail create-instances-from-snapshot \
        --instance-snapshot-name WordPress-1-1569866208 \
        --instance-names WordPress-2 \
        --availability-zone us-west-2a \
        --bundle-id small_3_0

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "WordPress-2",
                "resourceType": "Instance",
                "createdAt": 1569865914.908,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationType": "CreateInstancesFromSnapshot",
                "status": "Started",
                "statusChangedAt": 1569865914.908
            }
        ]
    }

For more information, see `Create Lightsail instances from snapshots <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-create-instance-from-snapshot.html>`__ in the *Amazon Lightsail User Guide*.
