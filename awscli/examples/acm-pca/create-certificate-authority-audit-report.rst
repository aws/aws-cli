**To create a certificate authority audit report**

The following ``create-certificate-authority-audit-report`` example creates an audit report for the private CA identified by the ARN. ::

    aws acm-pca create-certificate-authority-audit-report \
        --certificate-authority-arn arn:aws:acm-pca:us-east-1:accountid:certificate-authority/12345678-1234-1234-1234-123456789012 \
        --s3-bucket-name your-bucket-name \
        --audit-report-response-format JSON

Output::

    {
        "AuditReportId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "S3Key": "audit-report/12345678-1234-1234-1234-123456789012/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111.json"
    }

For more information, see `Use audit reports with your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaAuditReport.html>`__ in the *AWS Private Certificate Authority User Guide*.
