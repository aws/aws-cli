**To verify a domain with Amazon SES**

The following ``verify-domain-identity`` example verifies a domain. ::

    aws ses verify-domain-identity \
        --domain example.com

Output::

    {
        "VerificationToken": "eoEmxw+YaYhb3h3iVJHuXMJXqeu1q1/wwmvjuEXAMPLE"
    }


To complete domain verification, you must add a TXT record with the returned verification token to your domain's DNS settings. For more information, see `Creating and verifying identities in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html>`__ in the *Amazon Simple Email Service Developer Guide*.
