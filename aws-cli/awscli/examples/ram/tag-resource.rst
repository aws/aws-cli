**To add tags to a resource share**

The following ``tag-resource`` example adds a tag key ``project`` and associated value ``lima`` to the specified resource share. ::

    aws ram tag-resource \
        --tags key=project,value=lima \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Update a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-update.html>`__ in the *AWS RAM User Guide*.
