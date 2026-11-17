**To create a certificate authority (CA) for a group**

The following ``create-group-certificate-authority`` example creates or rotates a CA for the specified group. ::

    aws greengrass create-group-certificate-authority \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "GroupCertificateAuthorityArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/certificateauthorities/d31630d674c4437f6c5dbc0dca56312a902171ce2d086c38e509c8EXAMPLEcc5"
    }

For more information, see `Overview of AWS IoT Greengrass security <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-sec.html>`__ in the *AWS IoT Greengrass Developer Guide*.
