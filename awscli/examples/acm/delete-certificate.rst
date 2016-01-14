[ :ref:`aws <cli:aws>` . :ref:`acm <cli:aws acm>` ]

.. _cli:aws acm delete-certificate:


******************
delete-certificate
******************



===========
Description
===========



Deletes a certificate and its associated private key. If this function succeeds, the certificate will no longer appear in the list of certificates that can be displayed by calling the  list-certificates function or be retrieved by calling the  get-certificate function. The certificate will not be available for use by other AWS services. 

.. note::

  You cannot delete a certificate that is being used by another AWS service. To delete a certificate that is in use, the certificate association must first be removed. 

 



========
Synopsis
========

::

    delete-certificate
  --certificate-arn <value>
  [--cli-input-json <value>]
  [--generate-cli-skeleton]




=======
Options
=======

``--certificate-arn`` (string)


  String that contains the ARN of the certificate to be deleted. This must be of the form: 

   

   ``arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012``  

   

  For more information about ARNs, see `Amazon Resource Names (ARNs) and AWS Service Namespaces`_ . 

  

``--cli-input-json`` (string)
Performs service operation based on the JSON string provided. The JSON string follows the format provided by ``--generate-cli-skeleton``. If other arguments are provided on the command line, the CLI values will override the JSON-provided values.

``--generate-cli-skeleton`` (boolean)
Prints a sample input JSON to standard output. Note the specified operation is not run if this argument is specified. The sample input can be used as an argument for ``--cli-input-json``.



========
Examples
========

**To delete an ACM certificate from your account**

The following ``delete-certificate`` command deletes the certificate with the specified ARN.

  aws acm delete-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
 




======
Output
======

None

.. _Amazon Resource Names (ARNs) and AWS Service Namespaces: http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
