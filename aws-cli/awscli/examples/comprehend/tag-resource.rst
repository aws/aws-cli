**Example 1: To tag a resource**

The following ``tag-resource`` example adds a single tag to an Amazon Comprehend resource. ::

    aws comprehend tag-resource \
        --resource-arn arn:aws:comprehend:us-west-2:123456789012:document-classifier/example-classifier/version/1 \
        --tags Key=Location,Value=Seattle

This command produces no output.

For more information, see `Tagging your resources <https://docs.aws.amazon.com/comprehend/latest/dg/tagging.html>`__ in the *Amazon Comprehend Developer Guide*.

**Example 2: To add multiple tags to a resource**

The following ``tag-resource`` example adds multiple tags to an Amazon Comprehend resource. ::

    aws comprehend tag-resource \
        --resource-arn "arn:aws:comprehend:us-west-2:123456789012:document-classifier/example-classifier/version/1" \
        --tags Key=location,Value=Seattle Key=Department,Value=Finance

This command produces no output.

For more information, see `Tagging your resources <https://docs.aws.amazon.com/comprehend/latest/dg/tagging.html>`__ in the *Amazon Comprehend Developer Guide*.