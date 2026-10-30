**To list all identities (email addresses and domains) for a specific AWS account**


The following ``list-identities`` example lists all identities that have been submitted for verification with Amazon SES. ::

    aws ses list-identities

Output::

    {
        "Identities": [
            "user@example.com",
            "example.com"
        ]
    }


The list that is returned contains all identities regardless of verification status (verified, pending verification, failure, etc.).

In this example, email addresses *and* domains are returned because we did not specify the identity-type parameter.

For more information about verification, see `Verifying Email Addresses and Domains in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Verifying Email Addresses and Domains in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html
