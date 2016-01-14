[ :ref:`aws <cli:aws>` . :ref:`acm <cli:aws acm>` ]

.. _cli:aws acm describe-certificate:


********************
describe-certificate
********************



===========
Description
===========



Returns a list of the fields contained in the specified certificate. For example, this function returns the certificate status, a flag that indicates whether the certificate is associated with any other AWS service, and the date at which the certificate request was created. The certificate is specified on input by its Amazon Resource Name (ARN). 



========
Synopsis
========

::

    describe-certificate
  --certificate-arn <value>
  [--cli-input-json <value>]
  [--generate-cli-skeleton]




=======
Options
=======

``--certificate-arn`` (string)


  String that contains a certificate ARN. The ARN must be of the form: 

   

   ``arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012``  

   

  For more information about ARNs, see `Amazon Resource Names (ARNs) and AWS Service Namespaces`_ . 

  

``--cli-input-json`` (string)
Performs service operation based on the JSON string provided. The JSON string follows the format provided by ``--generate-cli-skeleton``. If other arguments are provided on the command line, the CLI values will override the JSON-provided values.

``--generate-cli-skeleton`` (boolean)
Prints a sample input JSON to standard output. Note the specified operation is not run if this argument is specified. The sample input can be used as an argument for ``--cli-input-json``.



========
Examples
========

**To retrieve the fields contained in an ACM certificate**

The following ``describe-certificate`` command retrieves all of the fields for the certificate with the specified ARN.

  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
 
Output similar to the following is displayed:

{
  "Certificate": {
    "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012", 
    "CreatedAt": 1446835267.0, 
    "DomainName": "www.example.com", 
    "DomainValidationOptions": [
      {
        "DomainName": "www.example.com", 
        "ValidationDomain": "www.example.com", 
        "ValidationEmails": [
          "hostmaster@example.com", 
          "admin@example.com", 
          "owner@example.com.whoisprivacyservice.org", 
          "tech@example.com.whoisprivacyservice.org", 
          "admin@example.com.whoisprivacyservice.org", 
          "postmaster@example.com", 
          "webmaster@example.com", 
          "administrator@example.com"
        ]
      }, 
      {
        "DomainName": "www.example.net", 
        "ValidationDomain": "www.example.net", 
        "ValidationEmails": [
          "postmaster@example.net", 
          "admin@example.net", 
          "owner@example.net.whoisprivacyservice.org", 
          "tech@example.net.whoisprivacyservice.org", 
          "admin@example.net.whoisprivacyservice.org", 
          "hostmaster@example.net", 
          "administrator@example.net", 
          "webmaster@example.net"
        ]
      }
    ], 
    "InUseBy": [], 
    "IssuedAt": 1446835815.0, 
    "Issuer": "Amazon", 
    "KeyAlgorithm": "RSA-2048", 
    "NotAfter": 1478433600.0, 
    "NotBefore": 1446768000.0, 
    "Serial": "0f:ac:b0:a3:8d:ea:65:52:2d:7d:01:3a:39:36:db:d6", 
    "SignatureAlgorithm": "SHA256WITHRSA", 
    "Status": "ISSUED", 
    "Subject": "CN=www.example.com", 
    "SubjectAlternativeNames": [
      "www.example.com", 
      "www.example.net"
    ]
  }
}





======
Output
======

Certificate -> (structure)

  

  Contains a  CertificateDetail structure that lists the certificate fields.

  

  CertificateArn -> (string)

    

    Amazon Resource Name (ARN) of the certificate. This is of the form: 

     

     ``arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012``  

     

    For more information about ARNs, see `Amazon Resource Names (ARNs) and AWS Service Namespaces`_ . 

    

    

  DomainName -> (string)

    

    Fully qualified domain name (FQDN), such as www.example.com or example.com, for the certificate. 

    

    

  SubjectAlternativeNames -> (list)

    

    One or more domain names (subject alternative names) included in the certificate request. After the certificate is issued, this list includes the domain names bound to the public key contained in the certificate. The subject alternative names include the domain name (CN) of the certificate and additional domain names that can be used to connect to the website. 

    

    (string)

      

      

    

  DomainValidationOptions -> (list)

    

    References a  DomainValidation structure that contains the domain name in the certificate and the email address that can be used for validation. 

    

    (structure)

      

      Structure that contains the domain name, the base validation domain to which validation email is sent, and the email addresses used to validate the domain identity. 

      

      DomainName -> (string)

        

        Fully Qualified Domain Name (FQDN) of the form ``www.example.com or`` ``example.com``  

        

        

      ValidationEmails -> (list)

        

        A list of contact address for the domain registrant. 

        

        (string)

          

          

        

      ValidationDomain -> (string)

        

        The base validation domain that acts as the suffix of the email addresses that are used to send the emails. 

        

        

      

    

  Serial -> (string)

    

    String that contains the serial number of the certificate. 

    

    

  Subject -> (string)

    

    The X.500 distinguished name of the entity associated with the public key contained in the certificate. 

    

    

  Issuer -> (string)

    

    The X.500 distinguished name of the CA that issued and signed the certificate. 

    

    

  CreatedAt -> (timestamp)

    

    Time at which the certificate was requested. 

    

    

  IssuedAt -> (timestamp)

    

    Time at which the certificate was issued. 

    

    

  Status -> (string)

    

    A ``CertificateStatus`` enumeration value that can contain one of the following: 

     
    * PENDING_VALIDATION
     
    * ISSUED
     
    * INACTIVE
     
    * EXPIRED
     
    * REVOKED
     
    * FAILED
     
    * VALIDATION_TIMED_OUT
     

     

    

    

  RevokedAt -> (timestamp)

    

    The time, if any, at which the certificate was revoked. This value exists only if the certificate has been revoked. 

    

    

  RevocationReason -> (string)

    

    A ``RevocationReason`` enumeration value that indicates why the certificate was revoked. This value exists only if the certificate has been revoked. This can be one of the following vales: 

     
    * UNSPECIFIED
     
    * KEY_COMPROMISE
     
    * CA_COMPROMISE
     
    * AFFILIATION_CHANGED
     
    * SUPERCEDED
     
    * CESSATION_OF_OPERATION
     
    * CERTIFICATE_HOLD
     
    * REMOVE_FROM_CRL
     
    * PRIVILEGE_WITHDRAWN
     
    * A_A_COMPROMISE
     

     

    

    

  NotBefore -> (timestamp)

    

    Time before which the certificate is not valid. 

    

    

  NotAfter -> (timestamp)

    

    Time after which the certificate is not valid. 

    

    

  KeyAlgorithm -> (string)

    

    Asymmetric algorithm used to generate the public and private key pair. Currently the only supported value is ``RSA_2048`` . 

    

    

  SignatureAlgorithm -> (string)

    

    Algorithm used to generate a signature. Currently the only supported value is ``SHA256WITHRSA`` . 

    

    

  InUseBy -> (list)

    

    List that identifies ARNs that are using the certificate. A single ACM certificate can be used by multiple AWS resources. 

    

    (string)

      

      

    

  



.. _Amazon Resource Names (ARNs) and AWS Service Namespaces: http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
