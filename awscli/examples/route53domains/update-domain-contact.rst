**To update the contact information for a domain**

The following ``update-domain-contact`` command updates the contact information for a domain using the settings in the JSON-formatted file ``C:\temp\update-domain-contact.json``::

  aws route53 update-domain-contact --region us-east-1 --cli-input-json file://C:\temp\update-domain-contact.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Updating Contact Information for a Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Updating Contact Information for a Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-update-contacts.html#domain-update-contacts-basic

Use the following syntax for update-domain-contact.json::

  {
    "AdminContact": { 
      "AddressLine1": "string",
      "AddressLine2": "string",
      "City": "string",
      "ContactType": "string",
      "CountryCode": "string",
      "Email": "string",
      "ExtraParams": [ 
        { 
          "Name": "string",
          "Value": "string"
        }
      ],
      "Fax": "string",
      "FirstName": "string",
      "LastName": "string",
      "OrganizationName": "string",
      "PhoneNumber": "string",
      "State": "string",
      "ZipCode": "string"
    },
    "DomainName": "string",
    "RegistrantContact": { 
      "AddressLine1": "string",
      "AddressLine2": "string",
      "City": "string",
      "ContactType": "string",
      "CountryCode": "string",
      "Email": "string",
      "ExtraParams": [ 
        { 
          "Name": "string",
          "Value": "string"
        }
      ],
      "Fax": "string",
      "FirstName": "string",
      "LastName": "string",
      "OrganizationName": "string",
      "PhoneNumber": "string",
      "State": "string",
      "ZipCode": "string"
    },
    "TechContact": { 
      "AddressLine1": "string",
      "AddressLine2": "string",
      "City": "string",
      "ContactType": "string",
      "CountryCode": "string",
      "Email": "string",
      "ExtraParams": [ 
        { 
          "Name": "string",
          "Value": "string"
        }
      ],
      "Fax": "string",
      "FirstName": "string",
      "LastName": "string",
      "OrganizationName": "string",
      "PhoneNumber": "string",
      "State": "string",
      "ZipCode": "string"
    }
  }