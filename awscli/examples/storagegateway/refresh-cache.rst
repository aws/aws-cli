**To refresh the file share cache**

The following ``refresh-cache`` example refreshes the cache for the specified file share. ::

    aws storagegateway refresh-cache \
        --file-share-arn arn:aws:storagegateway:us-east-1:111122223333:share/share-2FA12345

Output::

    {
        "FileShareARN": "arn:aws:storagegateway:us-east-1:111122223333:share/share-2FA12345",
        "NotificationId": "4954d4b1-abcd-ef01-1234-97950a7d3483"
    }

For more information, see `Refreshing Amazon S3 bucket object cache <https://docs.aws.amazon.com/filegateway/latest/files3/refresh-cache.html>`__ in the *Amazon S3 File Gateway User Guide*.
