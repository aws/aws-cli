**To add or update tags for an AWS resource (for example: channel, stream key)**

The following ``tag-resource`` example adds or updates tags for a specified resource ARN (Amazon Resource Name). ::

    aws ivs tag-resource \
        --resource-arn arn:aws:ivs:us-west-2:123456789012:channel/abcdABCDefgh \
        --tags "tagkey1=tagvalue1, tagkey2=tagvalue2"

This command produces no output.

For more information, see `Best practices and strategies <https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
