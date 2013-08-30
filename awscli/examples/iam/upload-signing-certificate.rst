**To upload a signing certificate for an IAM user**

The following ``upload-signing-certificate`` commmand uploads a signing certificate for the IAM user named ``Bob``::

  aws iam upload-signing-certificate --user-name Bob --certificate-body file://certificate.pem

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      },
      "Certificate": {
          "UserName": "Bob",
          "Status": "Active",
          "CertificateBody": "-----BEGIN CERTIFICATE-----<certificate-body>-----END CERTIFICATE-----",
          "CertificateId": "TA7SMP42TDN5Z26OBPJE7EXAMPLE",
          "UploadDate": "2013-06-06T21:40:08.121Z"
      }
  }

The certificate is in a file named *certificate.pem* in PEM format.

For more information, see `Creating and Uploading a User Signing Certificate`_ in the *Using IAM* guide.

.. _`Creating and Uploading a User Signing Certificate`: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_UploadCertificate.html

