**To get the Amazon SES verification status for a list of identities**

The following ``get-identity-verification-attributes`` example retrieves the Amazon SES verification status for a list of identities. ::

    aws ses get-identity-verification-attributes \
        --identities "user1@example.com" "user2@example.com"

Output::

    {
        "VerificationAttributes": {
            "user1@example.com": {
                "VerificationStatus": "Success"
            },
            "user2@example.com": {
                "VerificationStatus": "Pending"
            }
        }
    }

If you call this command with an identity that you have never submitted for verification, that identity won't appear in the output.

For more information, see `Verified identities in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html>`__ in the *Amazon Simple Email Service Developer Guide*.
