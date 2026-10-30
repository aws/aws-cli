**To add tags to a MediaConnect resource**

The following ``tag-resource`` example adds a tag with a key name and value to the specified MediaConnect resource. ::

    aws mediaconnect tag-resource \
        --resource-arn arn:aws:mediaconnect:us-west-2:123456789012:flow:1-23aBC45dEF67hiJ8-12AbC34DE5fG:BasketballGame \
        --tags region=west

This command produces no output.

For more information, see `Tagging AWS Elemental MediaConnect resources <https://docs.aws.amazon.com/mediaconnect/latest/ug/tagging.html>`__ in the *AWS Elemental MediaConnect User Guide*.
