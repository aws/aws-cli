**To get the Amazon SES Easy DKIM attributes for a list of identities**

The following ``get-identity-dkim-attributes`` example retrieves the Amazon SES Easy DKIM attributes for a list of identities. ::

    aws ses get-identity-dkim-attributes \
        --identities "example.com" "user@example.com"

Output::

    {
        "DkimAttributes": {
            "example.com": {
                "DkimTokens": [
                    "EXAMPLEjcs5xoyqytjsotsijas7236gr",
                    "EXAMPLEjr76cvoc6mysspnioorxsn6ep",
                    "EXAMPLEkbmkqkhlm2lyz77ppkulerm4k"
                ],
                "DkimEnabled": true,
                "DkimVerificationStatus": "Success"
            },
            "user@example.com": {
                "DkimEnabled": false,
                "DkimVerificationStatus": "NotStarted"
            }
        }
    }

If you call this command with an identity that you have never submitted for verification, that identity won't appear in the output.

For more information, see `Easy DKIM in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim-easy.html>`__ in the *Amazon Simple Email Service Developer Guide*.
