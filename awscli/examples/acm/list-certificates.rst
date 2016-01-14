[ :ref:`aws <cli:aws>` . :ref:`acm <cli:aws acm>` ]

.. _cli:aws acm list-certificates:


*****************
list-certificates
*****************



===========
Description
===========



Retrieves a list of the certificate ARNs, and the domain name for each ARN, owned by the calling account. You can filter the list based on the ``certificate-statuses`` parameter, and you can display up to ``max-items`` certificates at one time. If you have more than ``max-items`` certificates, use the ``next-token`` marker from the response object in your next call to the ``list-certificates`` function to retrieve the next set of certificate ARNs. 



========
Synopsis
========

::

    list-certificates
  [--certificate-statuses <value>]
  [--next-token <value>]
  [--max-items <value>]
  [--cli-input-json <value>]
  [--generate-cli-skeleton]




=======
Options
=======

``--certificate-statuses`` (list)


  Identifies the status of the certificates for which you want to retrieve the certificate ARNs. This can be one or more of the following values: 

   
  * ``PENDING_VALIDATION`` 
   
  * ``ISSUED`` 
   
  * ``INACTIVE`` 
   
  * ``EXPIRED`` 
   
  * ``VALIDATION_TIMED_OUT`` 
   
  * ``REVOKED`` 
   
  * ``FAILED`` 
   

   

  



Syntax::

  "string" "string" ...

  Where valid values are:
    PENDING_VALIDATION
    ISSUED
    INACTIVE
    EXPIRED
    VALIDATION_TIMED_OUT
    REVOKED
    FAILED





``--next-token`` (string)


  String that contains an opaque marker of the next certificate to be displayed. Use this parameter when paginating results, and only in a subsequent request after you've received a response where the results have been truncated. Set it to an empty string the first time you call this function, and set it to the value of the ``next-token`` element you receive in the response object for subsequent calls. 

  

``--max-items`` (integer)


  Specify this parameter when paginating results to indicate the maximum number of certificates that you want to display for each response. If there are additional certificates beyond the maximum you specify, use the ``next-token`` value in your next call to the ``list-certificates`` function. 

  

``--cli-input-json`` (string)
Performs service operation based on the JSON string provided. The JSON string follows the format provided by ``--generate-cli-skeleton``. If other arguments are provided on the command line, the CLI values will override the JSON-provided values.

``--generate-cli-skeleton`` (boolean)
Prints a sample input JSON to standard output. Note the specified operation is not run if this argument is specified. The sample input can be used as an argument for ``--cli-input-json``.



========
Examples
========

**To list the ACM certificates for an AWS account**

The following ``list-certificates`` command lists the ARNs of the certificates in your account.

  aws acm list-certificates

The preceding command produces the following output:

{
    "CertificateSummaryList": [
        {
            "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012", 
            "DomainName": "www.example.com"
        }, 
        {
            "CertificateArn": "arn:aws:acm:us-east-1:493619779192:certificate/87654321-4321-4321-4321-210987654321", 
            "DomainName": "www.example.net"
        }
    ]
}

You can also filter your output by using the "certificate-statuses" argument. The following command displays certificates that have a PENDING_VALIDATION status.

  aws acm list-certificates --certificate-statuses PENDING_VALIDATION

Finally, you can decide how many certificates you want to display each time you call ``list-certificates``. For example, to display no more than two certificates at a time, set the ``max-items`` argument to 2 as in the following example. 

  aws acm list-certificates --max-items 2

Two certificate ARNs and a ``NextToken`` value will be displayed.

{
    "CertificateSummaryList": [
        {
            "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012", 
            "DomainName": "www.example.com"
        }, 
        {
            "CertificateArn": "arn:aws:acm:us-east-1:493619779192:certificate/87654321-4321-4321-4321-210987654321", 
            "DomainName": "www.example.net"
        }
    ], 
    "NextToken": "9f4d9f69-275a-41fe-b58e-2b837bd9ba48"
}
  
To display the next two certificates in your account, set this ``NextToken`` value in your next call.

  aws acm list-certificates --max-items 2 --next-token 9f4d9f69-275a-41fe-b58e-2b837bd9ba48




======
Output
======

NextToken -> (string)

  

  If the list has been truncated, this value is present and should be used for the ``next-token`` input parameter on your next call to ``list-certificates`` . 

  

  

CertificateSummaryList -> (list)

  

  A list of the certificate ARNs. 

  

  (structure)

    

    This structure is returned in the response object of  list-certificates function. 

    

    CertificateArn -> (string)

      

      Amazon Resource Name (ARN) of the certificate. This is of the form: 

       

       ``arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012``  

       

      For more information about ARNs, see `Amazon Resource Names (ARNs) and AWS Service Namespaces`_ . 

      

      

    DomainName -> (string)

      

      Fully qualified domain name (FQDN), such as www.example.com or example.com, for the certificate. 

      

      

    

  



.. _Amazon Resource Names (ARNs) and AWS Service Namespaces: http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
