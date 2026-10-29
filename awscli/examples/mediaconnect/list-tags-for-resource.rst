**To list tags for a MediaConnect resource**

The following ``list-tags-for-resource`` example displays the tag keys and values associated with the specified MediaConnect resource. ::

    aws mediaconnect list-tags-for-resource \
        --resource-arn arn:aws:mediaconnect:us-west-2:123456789012:flow:1-23aBC45dEF67hiJ8-12AbC34DE5fG:BasketballGame

Output::

    {
        "Tags": {
            "region": "west",
            "stage": "prod"
        }
    }

For more information, see `Tagging AWS Elemental MediaConnect resources <https://docs.aws.amazon.com/mediaconnect/latest/ug/tagging.html>`__ in the *AWS Elemental MediaConnect User Guide*.
