**To list the ACM certificates for an AWS account**

The following ``list-certificates`` example lists the ARNs of the certificates in your account. ::

    aws acm list-certificates

Output::

    {
        "CertificateSummaryList": [
            {
                "CertificateArn": "arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "DomainName": "www.example.com"
            },
            {
                "CertificateArn": "arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "DomainName": "www.example.net"
            }
        ]
    }

You can decide how many certificates you want to display each time you call ``list-certificates``. For example, if you have four certificates and you want to display no more than two at a time, set the ``max-items`` argument to 2 as in the following example. ::

    aws acm list-certificates \
        --max-items 2

Two certificate ARNs and a ``NextToken`` value are displayed.

Output::

    {
        "CertificateSummaryList": [
            {
                "CertificateArn": "arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "DomainName": "www.example.com"
            },
            {
                "CertificateArn": "arn:aws:acm:region:account:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "DomainName": "www.example.net"
            }
        ],
        "NextToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

To display the next two certificates in your account, set this ``NextToken`` value in your next call. ::

    aws acm list-certificates \
        --max-items 2 \
        --next-token a1b2c3d4-5678-90ab-cdef-EXAMPLE33333


You can filter your output by using the ``certificate-statuses`` argument. The following command displays certificates that have a PENDING_VALIDATION status. ::

    aws acm list-certificates \
        --certificate-statuses PENDING_VALIDATION

You can also filter your output by using the ``includes`` argument. The following command displays certificates filtered on the following properties. The certificates to be displayed:

- Specify that the RSA algorithm and a 2048 bit key are used to generate key pairs.
- Contain a Key Usage extension that specifies that the certificates can be used to create digital signatures.
- Contain an Extended Key Usage extension that specifies that the certificates can be used for code signing.

To display the certificates that have these properties, use the following command. ::

    aws acm list-certificates \
        --max-items 10 \
        --includes extendedKeyUsage=CODE_SIGNING,keyUsage=DIGITAL_SIGNATURE,keyTypes=RSA_2048

For more information, see `Search certificates managed by AWS Certificate Manager <https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-list.html>`__ in the *AWS Certificate Manager User Guide*.
