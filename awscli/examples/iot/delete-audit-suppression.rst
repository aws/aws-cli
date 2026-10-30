**To delete an audit finding suppression**

The following ``delete-audit-suppression`` example deletes an audit finding suppression for DEVICE_CERTIFICATE_EXPIRING_CHECK. ::

    aws iot delete-audit-suppression \
        --check-name DEVICE_CERTIFICATE_EXPIRING_CHECK \
        --resource-identifier deviceCertificateId="c7691e8b4a5f7d9e8c6b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d"

This command produces no output.

For more information, see `Audit finding suppressions <https://docs.aws.amazon.com/iot/latest/developerguide/audit-finding-suppressions.html>`__ in the *AWS IoT Developers Guide*.