**To retrieve the tags assigned to a behavior graph**

The following ``list-tags-for-resource`` example returns the tags assigned to the specified behavior graph. ::

    aws detective list-tags-for-resource \
        --resource-arn arn:aws:detective:us-west-2:123456789012:graph:027c7c4610ea4aacaf0b883093cab899

Output::

    {
        "Tags": {
            "Department" : "Finance"
        }
    }

For more information, see `Managing tags for a behavior graph <https://docs.aws.amazon.com/detective/latest/userguide/graph-tags.html>`__ in the *Amazon Detective Administration Guide*.