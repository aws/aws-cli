**To list the current CAs for a group**

The following ``list-group-certificate-authorities`` example lists the current certificate authorities (CAs) for the specified Greengrass group. ::

    aws greengrass list-group-certificate-authorities \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "GroupCertificateAuthorities": [
            {
                "GroupCertificateAuthorityArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/groups/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/certificateauthorities/f0430e1736ea8ed30cc5d5de9af67a7e3586bad9ae4d89c2a44163f65fdd8cf6",
                "GroupCertificateAuthorityId": "f0430e1736ea8ed30cc5d5de9af67a7e3586bad9ae4d89c2a44163f65fdd8cf6"
            }
        ]
    }

For more information, see `Certificate authority (CA) certificates <https://docs.aws.amazon.com/greengrass/v1/developerguide/device-auth.html#ca-certificates>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
