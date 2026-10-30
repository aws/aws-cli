**To upload a part of an archive**

The following ``upload-multipart-part`` example uploads the first 1 MiB (1024 x 1024 bytes) part of an archive. ::

    aws glacier upload-multipart-part \
        --body part1 \
        --range 'bytes 0-1048575/*' \
        --account-id - \
        --vault-name my-vault \
        --upload-id 19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ

Output::

    {
        "checksum": "e1f2a7cd6e047fa606fe2f0280350f69b9f8cfa602097a9a026360a7edc1f553"
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

The body parameter takes a path to a part file on the local filesystem. The range parameter takes an HTTP content range indicating the bytes that the part occupies in the completed archive. The upload ID is returned by the ``aws glacier initiate-multipart-upload`` command and can also be obtained by using ``aws glacier list-multipart-uploads``.

For more information on multipart uploads to Amazon Glacier using the AWS CLI, see `Using Amazon Glacier in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-glacier.html>`__ in the *AWS CLI User Guide*.
