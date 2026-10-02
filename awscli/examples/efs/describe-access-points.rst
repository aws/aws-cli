**To list all access points for a file system**

The following ``describe-access-points`` example lists all access points for a specified file system.::

    aws efs describe-access-points \
        --file-system-id fs-4gd2a78et

Output::

    {
    "AccessPoints": [
        {
            "AccessPointId": "fsap-0123456789abcdef0",
            "FileSystemId": "fs-4gd2a78et",
            "Name": "MyAccessPoint",
            "OwnerId": "123456789012",
            "LifeCycleState": "available",
            "RootDirectory": {
                "Path": "/my-app-data",
                "CreationInfo": {
                    "OwnerUid": 1001,
                    "OwnerGid": 1001,
                    "Permissions": "0755"
                }
            }
        }
    ]
}


This command lists all access points associated with the file system fs-4gd2a78et.

For more information, see `Amazon EFS Access Points <https://docs.aws.amazon.com/efs/latest/ug/efs-access-points.html>`__ in the *Amazon Elastic File System User Guide.*.