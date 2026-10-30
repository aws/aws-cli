**To retrieve the Resource Explorer view that is the default view for its AWS Region**

The following ``get-default-view`` example retrieves the ARN of the view that is the default for the AWS Region in which you call the operation. ::

    aws resource-explorer-2 get-default-view

Output::

    {
        "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/default-view/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Setting a default view in an AWS Region <https://docs.aws.amazon.com/resource-explorer/latest/userguide/configure-views-set-default.html>`__ in the *AWS Resource Explorer Users Guide*.