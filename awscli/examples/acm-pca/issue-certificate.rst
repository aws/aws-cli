**To issue a private certificate**

The ``issue-certificate`` command uses your private CA to issue a private certificate::

  aws acm-pca issue-certificate --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --csr file://C:\cert_1.csr --signing-algorithm "SHA256WITHRSA" --validity Value=365,Type="DAYS" --idempotency-token 1234