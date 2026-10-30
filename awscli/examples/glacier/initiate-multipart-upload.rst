**To start a multipart upload**

The following ``initiate-multipart-upload`` example initiates a multipart upload to a vault named ``my-vault`` with a part size of 1 MiB (1024 x 1024 bytes) per file. ::

    aws glacier initiate-multipart-upload \
        --account-id - \
        --part-size 1048576 \
        --vault-name my-vault \
        --archive-description "multipart upload test"

Output::

    {
        "location": "/123456789012/vaults/my-vault/multipart-uploads/19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ",
        "uploadId": "19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ"
    }

The archive description parameter is optional. Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

This command outputs an upload ID when successful. Use the upload ID when uploading each part of your archive with ``aws glacier upload-multipart-part``. For more information on multipart uploads to Amazon Glacier using the AWS CLI, see `Using Amazon Glacier in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-glacier.html>`__ in the *AWS CLI User Guide*.
