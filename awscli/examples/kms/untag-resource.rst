**To delete a tag from an AWS KMS CMK**

The following ``untag-resource`` example deletes the tag with the ``"Purpose"`` key from a customer managed CMK. 

To specify the CMK, use the ``key-id`` parameter. This example uses a key ID value, but you can use a key ID or key ARN in this command. Before running this command, replace the example key ID with a valid key ID from your AWS account. ::

    aws kms untag-resource \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab \
        --tag-key 'Purpose'

This command produces no output. To view the tags on an AWS KMS CMK, use the ``list-resource-tags`` command.

For more information about using tags in AWS KMS, see `Tagging Keys <https://docs.aws.amazon.com/kms/latest/developerguide/tagging-keys.html>`__ in the *AWS Key Management Service Developer Guide*.