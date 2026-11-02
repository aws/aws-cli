**To refresh the file share cache**

The following ``refresh-cache`` example refreshes the cache for the specified file share. ::

    aws storagegateway refresh-cache \
        --file-share-arn arn:aws:storagegateway:us-west-2:123456789012:share/share-2FA12345

Output::

    {
        "FileShareARN": "arn:aws:storagegateway:us-west-2:123456789012:share/share-2FA12345",
        "NotificationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Refreshing Amazon S3 bucket object cache <https://docs.aws.amazon.com/filegateway/latest/files3/refresh-cache.html>`__ in the *Amazon S3 File Gateway User Guide*.
