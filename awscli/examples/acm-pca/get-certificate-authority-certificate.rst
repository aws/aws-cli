**To retrieve a certificate authority (CA) certificate**

The ``get-certificate-authority-certificate`` command retrieves the certificate and certificate chain for your private CA::

  aws acm-pca get-certificate-authority-certificate --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --output text