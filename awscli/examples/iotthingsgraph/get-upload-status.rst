**To get the status of your entity upload**

The following ``get-upload-status`` example gets the status of your entity upload operation. The value of ``MyUploadId`` is the ID value returned by the ``upload-entity-definitions`` operation. ::

    aws iotthingsgraph get-upload-status \
        --upload-id "MyUploadId"

Output::

    {
        "namespaceName": "us-west-2/123456789012/default",
        "namespaceVersion": 5,
        "uploadId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "uploadStatus": "SUCCEEDED"
    }
