**Example 1: To view specific inventory type entries for an instance**

The following ``list-inventory-entries`` example lists the inventory entries for the AWS:Application inventory type on a specific instance. ::

    aws ssm list-inventory-entries \
        --instance-id "i-1234567890abcdef0" \
        --type-name "AWS:Application"

Output::

    {
        "TypeName": "AWS:Application",
        "InstanceId": "i-1234567890abcdef0",
        "SchemaVersion": "1.1",
        "CaptureTime": "2019-02-15T12:17:55Z",
        "Entries": [
            {
                "Architecture": "i386",
                "Name": "Amazon SSM Agent",
                "PackageId": "{a1b2c3d4-5678-90ab-cdef-EXAMPLE11111}",
                "Publisher": "Amazon Web Services",
                "Version": "2.3.274.0"
            },
            {
                "Architecture": "x86_64",
                "InstalledTime": "2018-05-03T13:42:34Z",
                "Name": "AmazonCloudWatchAgent",
                "Publisher": "",
                "Version": "1.200442.0"
            }
        ]
    }

For more information, see `AWS Systems Manager Inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-inventory.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To view custom inventory entries assigned to an instance**

The following ``list-inventory-entries`` example lists a custom inventory entry assigned to an instance. ::

    aws ssm list-inventory-entries \
        --instance-id "i-1234567890abcdef0" \
        --type-name "Custom:RackInfo"

Output::

    {
        "TypeName": "Custom:RackInfo",
        "InstanceId": "i-1234567890abcdef0",
        "SchemaVersion": "1.0",
        "CaptureTime": "2021-05-22T10:01:01Z",
        "Entries": [
            {
                "RackLocation": "Bay B/Row C/Rack D/Shelf E"
            }
        ]
    }

For more information, see `Assigning custom inventory metadata to a managed node <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom-metadata.html>`__ in the *AWS Systems Manager User Guide*.
