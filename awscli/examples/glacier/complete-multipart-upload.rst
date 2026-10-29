**To complete a multipart upload**

The following ``complete-multipart-upload`` example completes multipart upload for a 3 MiB archive. ::

    aws glacier complete-multipart-upload \
        --archive-size 3145728 \
        --checksum 9628195fcdbcbbe76cdde456d4646fa7de5f219fb39823836d81f0cc0e18aa67 \
        --upload-id 19gaRezEXAMPLES6Ry5YYdqthHOC_kGRCT03L9yetr220UmPtBYKk-OssZtLqyFu7sY1_lR7vgFuJV6NtcV5zpsJ \
        --account-id - \
        --vault-name my-vault

Output::

    {
        "location": "/123456789012/vaults/my-vault/archives/kKB7ymWJVpPSwhGP6ycSOAekp9ZYe_--zM_mw6k76ZFGEIWQX-ybtRDvc2VkPSDtfKmQrj0IRQLSGsNuDp-AJVlu2ccmDSyDUmZwKbwbpAdGATGDiB3hHO0bjbGehXTcApVud_wyDw",
        "checksum": "9628195fcdbcbbe76cdde456d4646fa7de5f219fb39823836d81f0cc0e18aa67",
        "archiveId": "kKB7ymWJVpPSwhGP6ycSOAekp9ZYe_--zM_mw6k76ZFGEIWQX-ybtRDvc2VkPSDtfKmQrj0IRQLSGsNuDp-AJVlu2ccmDSyDUmZwKbwbpAdGATGDiB3hHO0bjbGehXTcApVud_wyDw"
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

The upload ID is returned by the ``aws glacier initiate-multipart-upload`` command and can also be obtained by using ``aws glacier list-multipart-uploads``. The checksum parameter takes a SHA-256 tree hash of the archive in hexadecimal.

For more information on multipart uploads to Amazon Glacier using the AWS CLI, including instructions on calculating a tree hash, see `Using Amazon Glacier in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-services-glacier.html>`__ in the *AWS CLI User Guide*.

For more information, see `Uploading Large Archives in Parts (Multipart Upload) <https://docs.aws.amazon.com/amazonglacier/latest/dev/uploading-archive-mpu.html>`__ in the *Amazon Glacier Developer Guide*.
