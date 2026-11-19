**To modify the throughput mode of a file system**

The following ``update-file-system`` example changes the throughput mode of an existing file system to provisioned and sets the provisioned throughput to 50 MiB/s.::

    aws efs update-file-system \
        --file-system-id fs-4gd2a78et \
        --throughput-mode provisioned \
        --provisioned-throughput-in-mibps 50


Output::

    {
        "FileSystemId": "fs-4gd2a78et",
        "LifeCycleState": "available",
        "ThroughputMode": "provisioned",
        "ProvisionedThroughputInMibps": 50.0
    }


This command updates the throughput mode of the file system with the ID fs-c7a0456e to provisioned mode with 50 MiB/s of throughput.

For more information, see `Amazon EFS Performance <https://docs.aws.amazon.com/efs/latest/ug/performance.html>`__ in the *Amazon Elastic File System User Guide.*.