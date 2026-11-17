**To update the expiry of a group's certificates**

The following ``update-group-certificate-configuration`` example sets a 10-day expiry for the certificates generated for the specified group. ::

    aws greengrass update-group-certificate-configuration \
        --group-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --certificate-expiry-in-milliseconds 864000000

Output::

    {
        "CertificateExpiryInMilliseconds": "864000000",
        "CertificateAuthorityExpiryInMilliseconds": "2524607999000",
        "GroupId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Overview of AWS IoT Greengrass security <https://docs.aws.amazon.com/greengrass/v1/developerguide/gg-sec.html>`__ in the *AWS IoT Greengrass Developer Guide*.
