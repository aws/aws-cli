**To update the configuration of your private certificate authority**

The ``update-certificate-authority`` command updates the status and configuration of your private CA::

  aws acm-pca update-certificate-authority --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-1232456789012 --revocation-configuration file://C:\revoke_config.txt --status "DISABLED"