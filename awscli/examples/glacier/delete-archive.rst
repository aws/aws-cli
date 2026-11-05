**To delete an archive from a vault**

The following ``delete-archive`` example removes the specified archive from ``example_vault``. ::

    aws glacier delete-archive \
        --account-id 123456789012  \
        --vault-name example_vault \
        --archive-id Sc0u9ZP8yaWkmh-XGlIvAVprtLhaLCGnNwNl5I5x9HqPIkX5mjc0DrId3Ln-Gi_k2HzmlIDZUz117KSdVMdMXLuFWi9PJUitxWO73edQ43eTlMWkH0pd9zVSAuV_XXZBVhKhyGhJ7w

This command produces no output.

For more information, see `Deleting an Archive in Amazon Glacier <https://docs.aws.amazon.com/amazonglacier/latest/dev/deleting-an-archive.html>`__ in the *Amazon Glacier Developer Guide*.
