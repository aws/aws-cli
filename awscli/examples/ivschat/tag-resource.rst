**To add or update tags for an AWS resource (for example: Room)**

The following ``tag-resource`` example adds or updates tags for a specified resource ARN (Amazon Resource Name). On success it returns HTTP 200 with an empty response body. ::

    aws ivschat tag-resource \
        --resource-arn arn:aws:ivschat:us-west-2:12345689012:room/g1H2I3j4k5L6 \
        --tags "tagkey1=tagkeyvalue1, tagkey2=tagkeyvalue2"

This command produces no output.

For more information, see `Best practices and strategies <https://docs.aws.amazon.com/tag-editor/latest/userguide/best-practices-and-strats.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.