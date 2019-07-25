**To view specific inventory type entries for an instance**

This example lists the inventory entries for the AWS:Application inventory type on a specific instance.

Command::

  aws ssm list-inventory-entries --instance-id "i-1234567890abcdef0" --type-name "AWS:Application"

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
            "PackageId": "{88a60be2-89a1-4df8-812a-80863c2a2b68}",
            "Publisher": "Amazon Web Services",
            "Version": "2.3.274.0"
        },
        {
            "Architecture": "x86_64",
            "InstalledTime": "2018-05-03T13:42:34Z",
            "Name": "AmazonCloudWatchAgent",
            "Publisher": "",
            "Version": "1.200442.0"
        },
        ...
    ]
  }
