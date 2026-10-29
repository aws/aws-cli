**To abort a multipart upload**

The following ``abort-multipart-upload`` example deletes an in-progress multipart upload to a vault named ``my-vault``. ::

    aws glacier abort-multipart-upload \
        --account-id - \
        --vault-name my-vault \
        --upload-id 19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ

This command produces no output. Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account. The upload ID is returned by the ``aws glacier initiate-multipart-upload`` command and can also be obtained by using ``aws glacier list-multipart-uploads``.

For more information on multipart uploads to Amazon Glacier using the AWS CLI, see `Using Amazon Glacier in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-glacier.html>`__ in the *AWS CLI User Guide*.

For more information, see `Uploading Large Archives in Parts (Multipart Upload) <https://docs.aws.amazon.com/amazonglacier/latest/dev/uploading-archive-mpu.html>`__ in the *Amazon Glacier Developer Guide*.
