**To retrieve an issued certificate**

The ``get-certificate`` command retrieves a base64 encoded PEM format certificate::

  aws acm-pca get-certificate --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --certificate-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012/certificate/6707447683a9b7f4055627ffd55cebcc --output text