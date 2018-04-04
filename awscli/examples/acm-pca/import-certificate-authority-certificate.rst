**To import your certificate authority certificate into ACM PCA**

The ``import-certificate-authority-certificate`` command imports your signed private CA certificate into ACM PCA::

  aws acm-pca import-certificate-authority-certificate --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --certificate file://C:\ca_cert.pem --certificate-chain file://C:\ca_cert_chain.pem