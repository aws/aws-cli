**To upload a signing certificate for an IAM user**

The following ``upload-signing-certificate`` example uploads a signing certificate for the IAM user named ``Bob``. ::

    aws iam upload-signing-certificate \
        --user-name Bob \
        --certificate-body file://certificate.pem

Contents of ``certificate.pem``::

    -----BEGIN CERTIFICATE-----
    MIICdzCCAeCgAwIBAgIGANc+EXAMPLE...
    -----END CERTIFICATE-----

Output::

    {
        "Certificate": {
            "UserName": "Bob",
            "Status": "Active",
            "CertificateBody": "-----BEGIN CERTIFICATE-----<certificate-body>-----END CERTIFICATE-----",
            "CertificateId": "TA7SMP42TDN5Z26OBPJE7EXAMPLE",
            "UploadDate": "2013-06-06T21:40:08.121Z"
        }
    }

The certificate is in a file named *certificate.pem* in PEM format.

For more information, see `Set up the Amazon EC2 AMI tools <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/set-up-ami-tools.html#ami-tools-managing-certs>`__ in the *Amazon EC2 User Guide*.
