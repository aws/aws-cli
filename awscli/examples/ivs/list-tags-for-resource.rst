**To list all tags for an AWS resource (for example: channel, stream key)**

The following ``list-tags-for-resource`` example lists all tags for a specified resource ARN (Amazon Resource Name). ::

    aws ivs list-tags-for-resource \
        --resource-arn arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh

This command produces no output.

For more information, see `Tagging <https://docs.aws.amazon.com/ivs/latest/APIReference/Welcome.html>`__ in the *Amazon Interactive Video Service API Reference*.