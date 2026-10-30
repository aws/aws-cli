**To retrieve the access policy of a vault**

The following ``get-vault-access-policy`` example retrieves the access policy for the specified vault. ::

    aws glacier get-vault-access-policy \
        --account-id 123456789111 \
        --vault-name example_vault

Output::

    {
        "policy": {
            "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789222:root\"},\"Action\":\"glacier:ListJobs\",\"Resource\":\"arn:aws:glacier:us-west-2:123456789111:vaults/example_vault\"},{\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789222:root\"},\"Action\":\"glacier:UploadArchive\",\"Resource\":\"arn:aws:glacier:us-west-2:123456789111:vaults/example_vault\"}]}"
        }
    }

For more information, see `Vault Access Policies <https://docs.aws.amazon.com/amazonglacier/latest/dev/vault-access-policy.html>`__ in the *Amazon Glacier Developer Guide*.
