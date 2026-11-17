**To retrieve the configuration for the certificate authority used by the Greengrass group**

The following ``get-group-certificate-configuration`` example retrieves the configuration for the certificate authority (CA) used by the specified Greengrass group. ::

    aws greengrass get-group-certificate-configuration \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    
Output::

    {
        "CertificateAuthorityExpiryInMilliseconds": "2524607999000",
        "CertificateExpiryInMilliseconds": "604800000",
        "GroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Overview of AWS IoT Greengrass security <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-sec.html>`__ in the *AWS IoT Greengrass Developer Guide*.
