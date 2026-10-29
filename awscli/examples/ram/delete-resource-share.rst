**To delete a resource share**

The following ``delete-resource-share`` example deletes the specified resource share. ::

    aws ram delete-resource-share \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "returnValue": true
    }

For more information, see `Deleting a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-delete.html>`__ in the *AWS RAM User Guide*.
