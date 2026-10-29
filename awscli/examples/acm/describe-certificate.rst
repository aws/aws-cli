**To retrieve the fields contained in an ACM certificate**

The following ``describe-certificate`` example retrieves all of the fields for the certificate with the specified ARN. ::

    aws acm describe-certificate \
        --certificate-arn arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111
 
Output::

    {
        "Certificate": {
            "CertificateArn": "arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreatedAt": 1446835267.0,
            "DomainName": "www.example.com",
            "DomainValidationOptions": [
                {
                    "DomainName": "www.example.com",
                    "ValidationDomain": "www.example.com",
                    "ValidationEmails": [
                        "hostmaster@example.com",
                        "admin@example.com",
                        "owner@example.com.whoisprivacyservice.org",
                        "tech@example.com.whoisprivacyservice.org",
                        "admin@example.com.whoisprivacyservice.org",
                        "postmaster@example.com",
                        "webmaster@example.com",
                        "administrator@example.com"
                    ]
                },
                {
                    "DomainName": "www.example.net",
                    "ValidationDomain": "www.example.net",
                    "ValidationEmails": [
                        "postmaster@example.net",
                        "admin@example.net",
                        "owner@example.net.whoisprivacyservice.org",
                        "tech@example.net.whoisprivacyservice.org",
                        "admin@example.net.whoisprivacyservice.org",
                        "hostmaster@example.net",
                        "administrator@example.net",
                        "webmaster@example.net"
                    ]
                }
            ],
            "InUseBy": [],
            "IssuedAt": 1446835815.0,
            "Issuer": "Amazon",
            "KeyAlgorithm": "RSA-2048",
            "NotAfter": 1478433600.0,
            "NotBefore": 1446768000.0,
            "Serial": "0f:ac:b0:a3:8d:ea:65:52:2d:7d:01:3a:39:36:db:d6",
            "SignatureAlgorithm": "SHA256WITHRSA",
            "Status": "ISSUED",
            "Subject": "CN=www.example.com",
            "SubjectAlternativeNames": [
                "www.example.com",
                "www.example.net"
            ]
        }
    }

For more information, see `View AWS Certificate Manager certificate details <https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-describe.html>`__ in the *AWS Certificate Manager User Guide*.
