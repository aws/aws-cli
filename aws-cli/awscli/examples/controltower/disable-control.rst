**To disable a Control Tower control**

The following ``disable-control`` example disables an AWS Control Tower enabled control. ::

    aws controltower disable-control \
        --control-identifier arn:aws:controlcatalog:::control/497wrm2xnk1wxlf4obrxxxxxx \
        --target-identifier arn:aws:organizations::123456789012:ou/o-s64ryxxxxx/ou-oqxx-i5wnxxxx

Output::

    {
        "operationIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `About controls in AWS Control Tower <https://docs.aws.amazon.com/controltower/latest/controlreference/controls.html>`__ in the *AWS Control Tower User Guide*.
