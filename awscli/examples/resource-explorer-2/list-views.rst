**To list the Resource Explorer views available in an AWS Region**

The following ``list-views`` example lists all of the views available in the Region in which you invoke the operation. ::

    aws resource-explorer-2 list-views

Output::

    {
        "Views": [
            "arn:aws:resource-explorer-2:us-west-2:123456789012:view/EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "arn:aws:resource-explorer-2:us-west-2:123456789012:view/Default-All-Resources-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "arn:aws:resource-explorer-2:us-west-2:123456789012:view/Production-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
        ]
    }

For more information about views, see `Working with views <https://docs.aws.amazon.com/resource-explorer/latest/userguide/views.html>`__ in the *AWS Resource Explorer Users Guide*.