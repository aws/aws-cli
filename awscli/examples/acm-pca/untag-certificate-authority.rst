**To remove one or more tags from your private certificate authority**

The ``untag-certificate-authority`` command removes tags from your private CA::

  aws acm-pca untag-certificate-authority --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --tags Key=Purpose,Value=Website