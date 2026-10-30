**To create a certificate authority audit report**

The following ``create-certificate-authority-audit-report`` example creates an audit report for the private CA identified by the ARN. ::

    aws acm-pca create-certificate-authority-audit-report \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:accountid:certificate-authority/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --s3-bucket-name your-bucket-name \
        --audit-report-response-format JSON

Output::

    {
        "AuditReportId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "S3Key": "audit-report/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111.json"
    }

For more information, see `Use audit reports with your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaAuditReport.html>`__ in the *AWS Private Certificate Authority User Guide*.
