**To get the tags on an AWS KMS CMK**

The following ``list-resource-tags`` example gets the tags for a CMK. To add or replace resource tags on CMKs, use the ``tag-resource`` command. The output shows that this CMK has two resource tags, each of which is comprised of a key and value.

To specify the CMK, use the ``key-id`` parameter. This example uses a key ID value, but you can use a key ID or key ARN in this command. ::

    aws kms list-resource-tags \
        --key-id 1234abcd-12ab-34cd-56ef-1234567890ab 

Output::

    {
        "Tags": [
        {
            "TagKey": "Dept",
            "TagValue": "IT"
        },
        {
            "TagKey": "Purpose",
            "TagValue": "Test"
        }
        ],
        "Truncated": false
    }

For more information about using tags in AWS KMS, see `Tagging Keys <https://docs.aws.amazon.com/kms/latest/developerguide/tagging-keys.html>`__ in the *AWS Key Management Service Developer Guide*.