**Example 1: To create a snapshot of a disk**

The following ``create-disk-snapshot`` example creates a snapshot named ``DiskSnapshot-1`` of the specified block storage disk. ::

    aws lightsail create-disk-snapshot \
        --disk-name Disk-1 \
        --disk-snapshot-name DiskSnapshot-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "resourceName": "DiskSnapshot-1",
                "resourceType": "DiskSnapshot",
                "createdAt": 1569625129.739,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "Disk-1",
                "operationType": "CreateDiskSnapshot",
                "status": "Started",
                "statusChangedAt": 1569625129.739
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "resourceName": "Disk-1",
                "resourceType": "Disk",
                "createdAt": 1569625129.739,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "DiskSnapshot-1",
                "operationType": "CreateDiskSnapshot",
                "status": "Started",
                "statusChangedAt": 1569625129.739
            }
        ]
    }

**Example 2: To create a snapshot of an instance's system disk**

The following ``create-disk-snapshot`` example creates a snapshot of the specified instance's system disk. ::

    aws lightsail create-disk-snapshot \
        --instance-name WordPress-1 \
        --disk-snapshot-name SystemDiskSnapshot-1

Output::

    {
        "operations": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "resourceName": "SystemDiskSnapshot-1",
                "resourceType": "DiskSnapshot",
                "createdAt": 1569625294.685,
                "location": {
                    "availabilityZone": "all",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "WordPress-1",
                "operationType": "CreateDiskSnapshot",
                "status": "Started",
                "statusChangedAt": 1569625294.685
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "resourceName": "WordPress-1",
                "resourceType": "Instance",
                "createdAt": 1569625294.685,
                "location": {
                    "availabilityZone": "us-west-2a",
                    "regionName": "us-west-2"
                },
                "isTerminal": false,
                "operationDetails": "SystemDiskSnapshot-1",
                "operationType": "CreateDiskSnapshot",
                "status": "Started",
                "statusChangedAt": 1569625294.685
            }
        ]
    }

For more information, see `Snapshots in Amazon Lightsail <https://lightsail.aws.amazon.com/ls/docs/en_us/articles/understanding-instance-snapshots-in-amazon-lightsail>`__ and `Creating a snapshot of an instance root volume in Amazon Lightsail <https://lightsail.aws.amazon.com/ls/docs/en_us/articles/amazon-lightsail-create-an-instance-root-volume-snapshot>`__ in the *Lightsail Developer Guide*.
