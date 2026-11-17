**To enable a Control Tower control**

The following ``enable-control`` example enables an AWS Control Tower control. ::

    aws controltower enable-control \
        --control-identifier arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrxxxxxx \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx

Output::

    {
        "arn": "arn:aws:controltower:us-west-2:123456789012:enabledcontrol/18J5KBJ3W3VTIRLV",
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.
