**To list tags for a resource**

The following ``list-tags-for-resource`` example lists tags for the specified resource. ::

    aws route53profiles list-tags-for-resource \
        --resource-arn arn:aws:route53profiles:us-west-2:123456789012:profile/rp-4987774726example

Output::

    {
        "Tags": {
            "my-key-2": "my-value-2",
            "my-key-1": "my-value-1"
        }
    }

For more information, see `Tagging Amazon Route 53 resources <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/tagging-resources.html>`__ in the *Amazon Route 53 Developer Guide*.
