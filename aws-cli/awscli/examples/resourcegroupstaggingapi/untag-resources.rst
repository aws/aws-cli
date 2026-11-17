**To remove a tag from a resource**

The following ``untag-resources`` example removes the specified tag keys and any associated values from the specified resource. ::

    aws resourcegroupstaggingapi untag-resources \
        --resource-arn-list arn:aws:s3:::amzn-s3-demo-bucket \
        --tag-keys Environment CostCenter

Output::

    {
        "FailedResourcesMap": {}
    }

For more information, see `Managing tags with Tag Editor <https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging-resources.html>`__ in the *Tagging AWS Resources and Tag Editor User Guide*.
