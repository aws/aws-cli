**To set a Resource Explorer view as the default for its AWS Region**

The following ``associate-default-view`` example sets a view, as specified by its ARN, to be the default view for the AWS Region in which you call the operation. ::

    aws resource-explorer-2 associate-default-view \
        --view-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-Main-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/My-Main-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Setting a default view in an AWS Region <https://docs.aws.amazon.com/resource-explorer/latest/userguide/configure-views-set-default.html>`__ in the *AWS Resource Explorer Users Guide*.