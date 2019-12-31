**To tag a CloudFront distribution**

The following example adds two tags to a CloudFront distribution by using
command line arguments::

    aws cloudfront tag-resource \
        --resource arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE \
        --tags Items=[{Key=Name,Value="Example name"},{Key=Project,Value="Example project"}]

Instead of using command line arguments, you can provide the tags in a JSON
file, as shown in the following example::

    aws cloudfront tag-resource \
        --resource arn:aws:cloudfront::123456789012:distribution/EDFDVBD6EXAMPLE \
        --tags file://tags.json

The file ``tags.json`` is a JSON document in the current folder that contains
the following::

    {
        "Items": [
            {
                "Key": "Name",
                "Value": "Example name"
            },
            {
                "Key": "Project",
                "Value": "Example project"
            }
        ]
    }

When successful, this command has no output.
