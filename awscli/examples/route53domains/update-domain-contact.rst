**To update the contact information for a domain**

The following ``update-domain-contact`` example updates the contact information for a domain, getting the parameters from the JSON-formatted file ``C:\temp\update-domain-contact.json``. 

This command runs only in the ``us-east-1`` Region. If your default region is set to ``us-east-1``, you can omit the ``region`` parameter. ::

    aws route53domains update-domain-contact \
        --region us-east-1 \
        --cli-input-json file://C:\temp\update-domain-contact.json

Contents of ``C:\temp\update-domain-contact.json``::

    {
        "AdminContact": {
            "AddressLine1": "101 Main Street",
            "AddressLine2": "Suite 1a",
            "City": "Seattle",
            "ContactType": "COMPANY",
            "CountryCode": "US",
            "Email": "w.xiulan@example.com",
            "FirstName": "Wang",
            "LastName": "Xiulan",
            "OrganizationName": "Example",
            "PhoneNumber": "+1.8005551212",
            "State": "WA",
            "ZipCode": "98101"
        },
        "DomainName": "example.com",
        "RegistrantContact": {
            "AddressLine1": "101 Main Street",
            "AddressLine2": "Suite 1a",
            "City": "Seattle",
            "ContactType": "COMPANY",
            "CountryCode": "US",
            "Email": "w.xiulan@example.com",
            "FirstName": "Wang",
            "LastName": "Xiulan",
            "OrganizationName": "Example",
            "PhoneNumber": "+1.8005551212",
            "State": "WA",
            "ZipCode": "98101"
        },
        "TechContact": {
            "AddressLine1": "101 Main Street",
            "AddressLine2": "Suite 1a",
            "City": "Seattle",
            "ContactType": "COMPANY",
            "CountryCode": "US",
            "Email": "w.xiulan@example.com",
            "FirstName": "Wang",
            "LastName": "Xiulan",
            "OrganizationName": "Example",
            "PhoneNumber": "+1.8005551212",
            "State": "WA",
            "ZipCode": "98101"
        }
    }

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To confirm that the operation succeeded, you can run `get-domain-detail <https://docs.aws.amazon.com/cli/latest/reference/route53domains/get-domain-detail.html>`__ . 
For more information, see `Updating Contact Information for a Domain <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-update-contacts.html#domain-update-contacts-basic>`__ in the *Amazon Route 53 Developer Guide*.
