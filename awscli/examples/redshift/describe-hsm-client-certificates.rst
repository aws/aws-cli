**To describe HSM client certificates**

The following ``describe-hsm-client-certificates`` example displays details for the specified HSM client certificate. ::

    aws redshift describe-hsm-client-certificates \
        --hsm-client-certificate-identifier myhsmclientcert

Output::

    {
        "HsmClientCertificates": [
            {
            "HsmClientCertificateIdentifier": "myhsmclientcert",
            "HsmClientCertificatePublicKey": "-----BEGIN CERTIFICATE-----\nEXAMPLECAfICCQD6m7oRw0uXOjANBgkqhkiG9w0BAQUFADCBiDELMAkGA1UEBhMC\nVVMxCzAJBgNVBAEXAMPLERAwDgYDVQQHEwdTZWF0dGxlMQ8wDQYDVQQKEwZBbWF6\nb24xFDASBgNVBAsTC0lBTSBDb25zEXAMPLEwEAYDVQQDEwlUZXN0Q2lsYWMxHzAd\nBgkqhkiG9w0BCQEWEG5vb25lQGFtYXpvbi5jb20wHhEXAMPLEDI1MjA0EXAMPLEN\nEXAMPLE0MjA0NTIxWjCBiDELMAkGA1UEBhMCVVMxCzAJBgNVBAgTAldBMRAwDgYD\nVQQHEwdTZWF0dGEXAMPLEQYDVQQKEwZBbWF6b24xFDASBgNVBAsTC0lBTSBDb25z\nb2xlMRIwEAYDVQQDEwlUZXN0Q2lsEXAMPLEdBgkqhkiG9w0BCQEWEG5vb25lQGFt\nYXpvbi5jb20wgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIEXAMPLEMaK0dn+a4GmWIWJ\n21uUSfwfEvySWtC2XADZ4nB+BLYgVIk60CpiwsZ3G93vUEIO3IyNoH/f0wYK8m9T\nrDHudUZg3qX4waLG5M43q7Wgc/MbQITxOUSQv7c7ugFFDzQGBzZswY67EXAMPLEE\nEXAMPLEZnzcvQAaRHhdlQWIMm2nrAgMBAAEwDQYJKoZIhvcNAQEFBQADgYEAtCu4\nnUhVVxYUntneD9EXAMPLE6q+auNKyExzyLwaxlAoo7TJHidbtS4J5iNmZgXL0Fkb\nFFBjvSfpJIlJ00zbhNYS5f6GuoEDEXAMPLEBHjJnyp378OD8uTs7fLvjx79LjSTb\nNYiytVbZPQUQ5Yaxu2jXnimvw3rEXAMPLE=\n-----END CERTIFICATE-----\n",
            "Tags": []
            }
        ]
    }

For more information, see `Amazon Redshift API Permissions Reference <https://docs.aws.amazon.com/redshift/latest/mgmt/redshift-policy-resources.resource-permissions.html>`__ in the *Amazon Redshift Cluster Management Guide*.
