**To add a tag to a KMS key**

The following ``tag-resource`` example adds ``"Purpose":"Test"`` and ``"Dept":"IT"`` tags to a customer managed KMS key. You can use tags like these to label KMS keys and create categories of KMS keys for permissions and auditing.

To specify the KMS key, use the ``key-id`` parameter. This example uses a key ID value, but you can use a key ID or key ARN in this command. ::

    aws kms tag-resource \
        --key-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tags TagKey='Purpose',TagValue='Test' TagKey='Dept',TagValue='IT'

This command produces no output. To view the tags on an AWS KMS KMS key, use the ``list-resource-tags`` command.

For more information about using tags in AWS KMS, see `Tagging keys <https://docs.aws.amazon.com/kms/latest/developerguide/tagging-keys.html>`__ in the *AWS Key Management Service Developer Guide*.