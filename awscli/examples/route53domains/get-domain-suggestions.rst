**To get a list of suggested domain names**

The following ``get-domain-suggestions`` command displays a list of suggested domain names based on the domain name ``example.com``. The response includes only domain names that are available. ::

    aws route53domains get-domain-suggestions \
        --domain-name example.com \
        --suggestion-count 10 \
        --only-available

Output::

    {
        "SuggestionsList": [
            {
                "DomainName": "egzaampal.com",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "examplelaw.com",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "examplehouse.net",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "homeexample.net",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "examplelist.com",
                "Availability": "AVAILABLE"
           },
            {
                "DomainName": "examplenews.net",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "officeexample.com",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "exampleworld.com",
                "Availability": "AVAILABLE"
            },
            {
                "DomainName": "exampleart.com",
                "Availability": "AVAILABLE"
            }
        ]
    }
