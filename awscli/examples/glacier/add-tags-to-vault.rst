**To add tags to a vault**

The following ``add-tags-to-vault`` example adds two tags to a vault named ``my-vault``. ::

    aws glacier add-tags-to-vault \
        --account-id - \
        --vault-name my-vault \
        --tags id=1234,date=july2015

This command produces no output.

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Tagging Amazon Glacier Resources <https://docs.aws.amazon.com/amazonglacier/latest/dev/tagging.html>`__ in the *Amazon Glacier Developer Guide*.
