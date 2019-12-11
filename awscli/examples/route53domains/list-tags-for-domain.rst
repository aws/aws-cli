**To list tags for a domain**

The following ``list-tags-for-domain`` command lists the tags that are currently associated with the specified domain. ::

    aws route53domains list-tags-for-domain \
        --domain-name example.com

Output::

    {
        "TagList": [
            {
                "Key": "key1",
                "Value": "value1"
            },
            {
                "Key": "key2",
                "Value": "value2"
            }
        ]
    }

For more information, see `Tagging Amazon Route 53 Resources <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/tagging-resources.html>`__ in the *Amazon Route 53 Developer Guide*.
