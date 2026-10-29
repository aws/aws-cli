**To revoke a private certificate**

The following ``revoke-certificate`` example revokes a private certificate from the CA identified by the ARN. ::

    aws acm-pca revoke-certificate \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:1234567890:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --certificate-serial 67:07:44:76:83:a9:b7:f4:05:56:27:ff:d5:5c:eb:cc \
        --revocation-reason "KEY_COMPROMISE"

This command produces no output.

For more information, see `Revoke a private certificate <https://docs.aws.amazon.com/privateca/latest/userguide/PcaRevokeCert.html>`__ in the *AWS Private Certificate Authority User Guide*.
