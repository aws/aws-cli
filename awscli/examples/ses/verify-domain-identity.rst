**To verify a domain with Amazon SES**

The following example uses the ``verify-domain-identity`` command to verify a domain::

    aws ses verify-domain-identity --domain example.com

Output::

 {
    "VerificationToken": "eoEmxw+YaYhb3h3iVJHuXMJXqeu1q1/wwmvjuEXAMPLE",
    "ResponseMetadata": {
        "RequestId": "9a50c7ce-d47a-11e2-aa3e-07064a188c70"
    }
 }


To complete domain verification, you must add a TXT record with the returned verification token to your domain's DNS settings. For more information, see `Verifying Domains in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Verifying Domains in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-domains.html
