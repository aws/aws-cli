**To create a certificate authority audit report**

The ``create-certificate-authority-audit-report`` command creates an audit report for your private CA::

  aws acm-pca create-certificate-authority-audit-report --certificate-authority-arn arn:aws:acm-pca:us-east-1:account:certificate-authority/12345678-1234-1234-1234-123456789012 --s3-bucket-name your-bucket-name --audit-report-response-format JSON