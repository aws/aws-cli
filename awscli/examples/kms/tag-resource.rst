**To add a tag to an AWS KMS CMK**

The following ``tag-resource`` example adds ``"Purpose":"Test"`` and ``"Dept":"IT"`` tags to a customer managed CMK. You can use tags like these to label CMKs and create categories of CMKs. 

To specify the CMK, use the ``key-id`` parameter. This example uses a key ID value, but you can use a key ID or key ARN in this command.

Before running this command, replace the example key ID with a valid key ID from your AWS account. ::

    aws kms tag-resource \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab \
        --tags TagKey='Purpose',TagValue='Test' TagKey='Dept',TagValue='IT'

This command produces no output. To view the tags on an AWS KMS CMK, use the ``list-resource-tags`` command.

For more information about using tags in AWS KMS, see `Tagging Keys <https://docs.aws.amazon.com/kms/latest/developerguide/tagging-keys.html>`__ in the *AWS Key Management Service Developer Guide*.