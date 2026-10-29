**To remove a tag from a vault**

The following ``remove-tags-from-vault`` example removes a tag with the key ``date`` from a vault named ``my-vault``. ::

    aws glacier remove-tags-from-vault \
        --account-id - \
        --vault-name my-vault \
        --tag-keys date

This command produces no output.

Amazon Glacier requires an account ID argument when performing operations, but you can use a hyphen to specify the in-use account.

For more information, see `Tagging Amazon Glacier Resources <https://docs.aws.amazon.com/amazonglacier/latest/dev/tagging.html>`__ in the *Amazon Glacier Developer Guide*.
