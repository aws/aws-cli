**To list the in-progress multipart uploads for a vault**

The following ``list-multipart-uploads`` example shows all of the in-progress multipart uploads for a vault named ``my-vault``. ::

    aws glacier list-multipart-uploads \
        --account-id - \
        --vault-name my-vault

Output::

    {
        "UploadsList": [
            {
                "MultipartUploadId": "19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ",
                "VaultARN": "arn:aws:glacier:us-west-2:123456789012:vaults/my-vault",
                "ArchiveDescription": "multipart upload test",
                "PartSizeInBytes": 1048576,
                "CreationDate": "2015-07-18T00:05:23.830Z"
            }
        ]
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information on multipart uploads to Amazon Glacier using the AWS CLI, see `Using Amazon Glacier in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-glacier.html>`__ in the *AWS CLI User Guide*.
