**To delete a resource share**

The following ``delete-resource-share`` example deletes the specified resource share. ::

    aws ram delete-resource-share \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE

Output::

    {
        "returnValue": true
    }

For more information, see `Deleting a resource share in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/working-with-sharing-delete.html>`__ in the *AWS RAM User Guide*.
