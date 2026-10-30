**To get details about an audit finding suppression**

The following ``describe-audit-suppression`` example gets details about the audit finding suppression for an expiring device certificate. ::

    aws iot describe-audit-suppression \
        --check-name DEVICE_CERTIFICATE_EXPIRING_CHECK \
        --resource-identifier deviceCertificateId=c7691e8b4a5f7d9e8c6b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d

Output::

    {
        "checkName": "DEVICE_CERTIFICATE_EXPIRING_CHECK",
        "resourceIdentifier": {
            "deviceCertificateId": "c7691e8b4a5f7d9e8c6b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d"
        },
        "expirationDate": "2020-08-20T00:00:00+00:00",
        "suppressIndefinitely": false
    }

For more information, see `Audit finding suppressions <https://docs.aws.amazon.com/iot/latest/developerguide/audit-finding-suppressions.html>`__ in the *AWS IoT Developers Guide*.