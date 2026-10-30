**To list file shares**

The following ``list-file-shares`` example lists the file shares for the specified gateway. ::

    aws storagegateway list-file-shares \
        --gateway-arn arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-FB02E292

Output::

    {
        "FileShareInfoList": [
            {
                "FileShareType": "NFS",
                "FileShareARN": "arn:aws:storagegateway:us-west-2:123456789012:share/share-2FA12345",
                "FileShareId": "share-2FA12345",
                "FileShareStatus": "AVAILABLE",
                "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-FB0AAAAA"
            }
        ],
        "Marker": null
    }

For more information, see `Managing your Amazon S3 File Gateway <https://docs.aws.amazon.com/filegateway/latest/files3/managing-gateway-file.html>`__ in the *Amazon S3 File Gateway User Guide*.
