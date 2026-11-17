**To remove tags from a resource share**

The following ``untag-resource`` example removes the ``project`` tag key and associated value from the specified resource share. ::

    aws ram untag-resource \
        --tag-keys project \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Update a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-update.html>`__ in the *AWS RAM User Guide*.
