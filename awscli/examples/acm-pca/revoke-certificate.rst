**To revoke a private certificate**

The ``revoke-certificate`` command revokes a private certificate::

  aws acm-pca revoke-certificate --certificate-authority-arn arn:aws:acm-pca:region:account:certificate-authority/12345678-1234-1234-1234-123456789012 --certificate-serial 67:07:44:76:83:a9:b7:f4:05:56:27:ff:d5:5c:eb:cc --revocation-reason "KEY_COMPROMISE"