[ :ref:`aws <cli:aws>` . :ref:`acm <cli:aws acm>` ]

.. _cli:aws acm request-certificate:


*******************
request-certificate
*******************



===========
Description
===========



Requests an ACM certificate for use with other AWS services. To request an ACM certificate, you must specify the fully qualified domain name (FQDN) for your site. You can also specify additional FQDNs if users can reach your site by using other names. For each domain name you specify, email is sent to the domain owner to request approval to issue the certificate. After receiving approval from the domain owner, the ACM certificate is issued. For more information, see the `AWS Certificate Manager User Guide`_ . 



========
Synopsis
========

::

    request-certificate
  --domain-name <value>
  [--subject-alternative-names <value>]
  [--idempotency-token <value>]
  [--domain-validation-options <value>]
  [--cli-input-json <value>]
  [--generate-cli-skeleton]




=======
Options
=======

``--domain-name`` (string)


  Fully qualified domain name (FQDN), such as www.example.com, of the site you want to secure with an SSL/TLS certificate. Use an asterisk (*) to create a wildcard certificate that protects several sites in the same domain. For example, *.example.com protects www.example.com, site.example.com, and images.example.com. 

  

``--subject-alternative-names`` (list)


  Additional FQDNs to be included in the Subject Alternative Name extension of the ACM certificate. For example, add the name www.example.net to a certificate for which the ``DomainName`` field is www.example.com if users can reach your site by using either name. 

  



Syntax::

  "string" "string" ...



``--idempotency-token`` (string)


  Customer chosen string that can be used to distinguish between calls to ``request-certificate`` . Idempotency tokens time out after one hour. Therefore, if you call ``request-certificate`` multiple times with the same idempotency token within one hour, ACM recognizes that you are requesting only one certificate and will issue only one. If you change the idempotency token for each call, ACM recognizes that you are requesting multiple certificates. 

  

``--domain-validation-options`` (list)


  The base validation domain that will act as the suffix of the email addresses that are used to send the emails. This must be the same as the ``Domain`` value or a super domain of the ``Domain`` value. For example, if you requested a certificate for ``www.example.com`` and specify **DomainValidationOptions** of ``example.com`` , ACM sends email to the domain registrant, technical contact, and administrative contact in WHOIS and the following five addresses: 

   
  * admin@example.com
   
  * administrator@example.com
   
  * hostmaster@example.com
   
  * postmaster@example.com
   
  * webmaster@example.com
   

   

  



Shorthand Syntax::

    DomainName=string,ValidationDomain=string ...




JSON Syntax::

  [
    {
      "DomainName": "string",
      "ValidationDomain": "string"
    }
    ...
  ]



``--cli-input-json`` (string)
Performs service operation based on the JSON string provided. The JSON string follows the format provided by ``--generate-cli-skeleton``. If other arguments are provided on the command line, the CLI values will override the JSON-provided values.

``--generate-cli-skeleton`` (boolean)
Prints a sample input JSON to standard output. Note the specified operation is not run if this argument is specified. The sample input can be used as an argument for ``--cli-input-json``.



========
Examples
========

**To request a new ACM certificate**

The following ``request-certificate`` command requests a new certificate for the www.example.com domain.

  aws acm request-certificate --domain-name www.example.com

You can enter an idempotency token to distinguish between calls to ``request-certificate``.

  aws acm request-certificate --domain-name www.example.com --idempotency-token 91adc45q

You can enter one or more alternative names that can be used to reach your website.

  aws acm request-certificate --domain-name www.example.com --idempotency-token 91adc45q --subject-alternative-names www.example.net

You can also enter domain validation options to specify the domain to which validation email will be sent.

  aws acm request-certificate --domain-name example.com --subject-alternative-names www.example.com --domain-validation-options DomainName=www.example.com,ValidationDomain=example.com
  




======
Output
======

CertificateArn -> (string)

  

  String that contains the ARN of the issued certificate. This must be of the form: 

   

   ``arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012``  

  

  



.. _AWS Certificate Manager User Guide: http://docs.aws.amazon.com/acm/latest/userguide/overview.html
