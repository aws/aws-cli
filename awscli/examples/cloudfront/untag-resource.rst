**To remove tags from a CloudFront distribution**

The following ``untag-resource`` example removes two tags from a CloudFront distribution by using
command line arguments. ::

    aws cloudfront untag-resource \
        --resource arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE \
        --tag-keys Items=Name,Project

This command produces no output.

Instead of using command line arguments, you can provide the tag keys in a JSON
file, as shown in the following example. ::

    aws cloudfront untag-resource \
        --resource arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE \
        --tag-keys file://tag-keys.json

Contents of ``tag-keys.json``::

    {
        "Items": [
            "Name",
            "Project"
        ]
    }

When successful, this command has no output.

For more information, see `Tag a CloudFront resource <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/tagging.html>`__ in the *Amazon CloudFront Developer Guide*.
