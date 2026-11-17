**To get a list of tagged resources**

The following ``get-resources`` example displays a list of resources in the account that are tagged with the specified key name and value. ::

    aws resourcegroupstaggingapi get-resources \
        --tag-filters Key=Environment,Values=Production \
        --tags-per-page 100

Output::

    {
        "ResourceTagMappingList": [
            {
                "ResourceARN": " arn:aws:inspector:us-west-2:123456789012:target/0-nvgVhaxX/template/0-7sbz2Kz0",
                "Tags": [
                    {
                        "Key": "Environment",
                        "Value": "Production"
                    }
                ]
            }
        ]
    }

For more information, see `Finding resources to tag <https://docs.aws.amazon.com/tag-editor/latest/userguide/find-resources-to-tag.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
