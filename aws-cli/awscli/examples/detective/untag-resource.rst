**To remove a tag value from a resource**

The following ``untag-resource`` example removes the Department tag from the specified behavior graph. ::

    aws detective untag-resource \
        --resource-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899 \
        --tag-keys "Department"

This command produces no output.

For more information, see `Managing tags for a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/graph-tags.html>`__ in the *Amazon Detective Administration Guide*.