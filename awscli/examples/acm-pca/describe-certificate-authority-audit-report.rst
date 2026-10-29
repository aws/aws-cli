**To describe an audit report for a certificate authority**

The following ``describe-certificate-authority-audit-report`` example lists information about the specified audit report for the CA identified by the ARN. ::

    aws acm-pca describe-certificate-authority-audit-report \
        --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/99999999-8888-7777-6666-555555555555 \
        --audit-report-id 11111111-2222-3333-4444-555555555555

Output::

    {
        "AuditReportStatus": "SUCCESS",
        "S3BucketName": "amzn-s3-demo-bucket",
        "S3Key": "audit-report/99999999-8888-7777-6666-555555555555/11111111-2222-3333-4444-555555555555.json",
        "CreatedAt": "2023-08-21T20:30:15.123000+00:00"
    }

For more information, see `Use audit reports with your private CA <https://docs.aws.amazon.com/privateca/latest/userguide/PcaAuditReport.html>`__ in the *AWS Private Certificate Authority User Guide*.
