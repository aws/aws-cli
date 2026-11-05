**To assign a tag to a resource**

The following ``tag-resource`` example assigns a value for the Department tag to the specified behavior graph. ::

    aws detective tag-resource \
        --resource-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899 \
        --tags '{"Department":"Finance"}'

This command produces no output.

For more information, see `Managing tags for a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/graph-tags.html>`__ in the *Amazon Detective Administration Guide*.