**To list the available shares of a HealthOmics analytics data**

The following ``list-shares`` example lists all shares that have been created for a resource-owner. ::

    aws omics list-shares \
        --resource-owner SELF

Output::

    {
        "shares": [
            {
                "shareId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "shareName": "myShare",
                "resourceArn": "arn:aws:omics:us-west-2:123456789111:variantStore/store_1",
                "principalSubscriber": "123456789012",
                "ownerId": "123456789111",
                "status": "PENDING"
            },
            {
                "shareId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "shareName": "myShare3456",
                "resourceArn": "arn:aws:omics:us-west-2:123456789111:variantStore/store_2",
                "principalSubscriber": "123456789012",
                "ownerId": "123456789111",
                "status": "ACTIVE"
            },
            {
                "shareId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "shareName": "myShare4",
                "resourceArn": "arn:aws:omics:us-west-2:123456789111:variantStore/store_3",
                "principalSubscriber": "123456789012",
                "ownerId": "123456789111",
                "status": "ACTIVE"
            }
        ]
    }

For more information, see `Cross-account sharing <https://docs.aws.amazon.com/omics/latest/dev/cross-account-sharing.html>`__ in the *AWS HealthOmics User Guide*.