**To upload an archive to a vault**

The following ``upload-archive`` example uploads an archive in the current folder named ``archive.zip`` to a vault named ``my-vault``. ::

    aws glacier upload-archive \
        --account-id - \
        --vault-name my-vault \
        --body archive.zip

Output::

    {
        "archiveId": "kKB7ymWJVpPSwhGP6ycSOAekp9ZYe_--zM_mw6k76ZFGEIWQX-ybtRDvc2VkPSDtfKmQrj0IRQLSGsNuDp-AJVlu2ccmDSyDUmZwKbwbpAdGATGDiB3hHO0bjbGehXTcApVud_wyDw",
        "checksum": "969fb39823836d81f0cc028195fcdbcbbe76cdde932d4646fa7de5f21e18aa67",
        "location": "/0123456789012/vaults/my-vault/archives/kKB7ymWJVpPSwhGP6ycSOAekp9ZYe_--zM_mw6k76ZFGEIWQX-ybtRDvc2VkPSDtfKmQrj0IRQLSGsNuDp-AJVlu2ccmDSyDUmZwKbwbpAdGATGDiB3hHO0bjbGehXTcApVud_wyDw"
    }

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

To retrieve an uploaded archive, initiate a retrieval job with the `aws glacier initiate-job <https://docs.aws.amazon.com/cli/latest/reference/glacier/initiate-job.html>`__ command.

For more information, see `Uploading an Archive in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/uploading-an-archive.html>`__ in the *Amazon Glacier Developer Guide*.
