**To upload a server certificate to your AWS account**

The following ``upload-server-certificate`` example uploads a server certificate to your AWS account. In this example, the certificate is in the file ``public_key_cert_file.pem``, the associated private key is in the file ``my_private_key.pem``, and the certificate chain provided by the certificate authority (CA) is in the ``my_certificate_chain_file.pem`` file. When the file has finished uploading, it is available under the name *myServerCertificate*. Parameters that begin with ``file://`` tell the command to read the contents of the file and use that as the parameter value instead of the file name itself. ::

    aws iam upload-server-certificate \
        --server-certificate-name myServerCertificate \
        --certificate-body file://public_key_cert_file.pem \
        --private-key file://my_private_key.pem \
        --certificate-chain file://my_certificate_chain_file.pem

Contents of ``public_key_cert_file.pem``::

    -----BEGIN CERTIFICATE-----
    MIIDXTCCAkWgAwIBAgIJAEXAMPLE...
    -----END CERTIFICATE-----

Contents of ``my_private_key.pem``::

    -----BEGIN PRIVATE KEY-----
    MIIEvQIBADANBgkqhkiG9w0BAQEFAAEXAMPLE...
    -----END PRIVATE KEY-----

Contents of ``my_certificate_chain_file.pem``::

    -----BEGIN CERTIFICATE-----
    MIIEkjCCA3qgAwIBAgIQEXAMPLE...
    -----END CERTIFICATE-----
    -----BEGIN CERTIFICATE-----
    MIIDSjCCAjKgAwIBAgIQEXAMPLE...
    -----END CERTIFICATE-----

Output::

    {
        "ServerCertificateMetadata": {
            "Path": "/",
            "ServerCertificateName": "myServerCertificate",
            "ServerCertificateId": "ASCAEXAMPLE123EXAMPLE",
            "Arn": "arn:aws:iam::1234567989012:server-certificate/myServerCertificate",
            "UploadDate": "2019-04-22T21:13:44+00:00",
            "Expiration": "2019-10-15T22:23:16+00:00"
        }
    }

For more information, see `Manage server certificates in IAM <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_server-certs.html>`__ in the *AWS IAM User Guide*.
