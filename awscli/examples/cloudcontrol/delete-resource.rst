**To delete a resource**

The following ``delete-resource`` example deletes a AWS::Kinesis::Stream resource with the identifier ResourceExample from your AWS account. ::

    aws cloudcontrol delete-resource \
        --type-name AWS::Kinesis::Stream \
        --identifier ResourceExample

Output::

    {
        "ProgressEvent": {
            "TypeName": "AWS::Kinesis::Stream",
            "Identifier": "ResourceExample",
            "RequestToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Operation": "DELETE",
            "OperationStatus": "IN_PROGRESS",
            "EventTime": 1632950300.14
        }
    }

For more information, see `Deleting a resource <https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/resource-operations-delete.html>`__ in the *Cloud Control API User Guide*.