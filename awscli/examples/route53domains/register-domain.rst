**To register a domain**

The following ``register-domain`` example registers a domain, retrieving all parameter values from a JSON-formatted file. 

This command runs only in the ``us-east-1`` Region. If your default region is set to ``us-east-1``, you can omit the ``region`` parameter. ::

    aws route53domains register-domain \
        --region us-east-1 \
        --cli-input-json file://register-domain.json

Contents of ``register-domain.json``::

    {
        "DomainName": "example.com",
        "DurationInYears": 1,
        "AutoRenew": true,
        "AdminContact": {
            "FirstName": "Martha",
            "LastName": "Rivera",
            "ContactType": "PERSON",
            "OrganizationName": "Example",
            "AddressLine1": "1 Main Street",
            "City": "Anytown",
            "State": "WA",
            "CountryCode": "US",
            "ZipCode": "98101",
            "PhoneNumber": "+1.8005551212",
            "Email": "mrivera@example.com"
        },
        "RegistrantContact": {
            "FirstName": "Li",
            "LastName": "Juan",
            "ContactType": "PERSON",
            "OrganizationName": "Example",
            "AddressLine1": "1 Main Street",
            "City": "Anytown",
            "State": "WA",
            "CountryCode": "US",
            "ZipCode": "98101",
            "PhoneNumber": "+1.8005551212",
            "Email": "ljuan@example.com"
        },
        "TechContact": {
            "FirstName": "Mateo",
            "LastName": "Jackson",
            "ContactType": "PERSON",
            "OrganizationName": "Example",
            "AddressLine1": "1 Main Street",
            "City": "Anytown",
            "State": "WA",
            "CountryCode": "US",
            "ZipCode": "98101",
            "PhoneNumber": "+1.8005551212",
            "Email": "mjackson@example.com"
        },
        "PrivacyProtectAdminContact": true,
        "PrivacyProtectRegistrantContact": true,
        "PrivacyProtectTechContact": true
    }

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To confirm that the operation succeeded, you can run ``get-operation-detail``. For more information, see `get-operation-detail <https://docs.aws.amazon.com/cli/latest/reference/route53domains/get-operation-detail.html>`__ . 

For information about which top-level domains (TLDs) require values for ``ExtraParams`` and what the valid values are, see `Domains that you can register with Amazon Route 53 <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/registrar-tld-list.html>`__ in the *Amazon Route 53 Developer Guide*.

For more information, see `Registering a New Domain <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html>`__ in the *Amazon Route 53 Developer Guide*.
