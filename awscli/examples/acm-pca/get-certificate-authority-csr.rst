**To retrieve the certificate signing request for a certificate authority**

The ``get-certificate-authority-csr`` command retrieves the CSR for your private CA::

  aws acm-pca get-certificate-authority-csr --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --output text