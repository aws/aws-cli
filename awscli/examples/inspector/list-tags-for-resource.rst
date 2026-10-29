**To list tags for resource**

The following ``list-tags-for-resource`` example lists all tags associated with the assessment template with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-gcwFliYu``. ::

    aws inspector list-tags-for-resource \
        --resource-arn arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-gcwFliYu

Output::

    {
        "tags": [
            {
                "key": "Name",
                "value": "Example"
            }
        ]
    }

