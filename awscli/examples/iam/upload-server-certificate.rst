**To upload a server certificate to your AWS account**

The following **upload-server-certificate** command uploads a server certificate to your AWS account::

  aws iam upload-server-certificate --server-certificate-name myServerCertificate --certificate-body file://public_key_cert_file.pem --private-key file://my_private_key.pem --certificate-chain file://my_certificate_chain_file.pem

The certificate is in the file ``public_key_cert_file.pem``, and your private key is in the file ``my_private_key.pem``.
When the file has finished uploading, it is available under the name *myServerCertificate*. The certificate chain
provided by the certificate authority (CA) is included as the ``my_certificate_chain_file.pem`` file.

Note that the parameters that contain file names are preceded with ``file://``. This tells the command that the
parameter value is a file name. You can include a complete path following ``file://``.

For more information, see `Creating, Uploading, and Deleting Server Certificates`_ in the *Using IAM* guide.

.. _`Creating, Uploading, and Deleting Server Certificates`: http://docs.aws.amazon.com/IAM/latest/UserGuide/InstallCert.html

