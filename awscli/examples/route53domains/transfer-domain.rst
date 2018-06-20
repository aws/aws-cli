**To transfer a domain to Amazon Route 53**

The following ``transfer-domain`` command transfers a domain to Route 53 using the settings in the JSON-formatted file ``C:\temp\transfer-domain.json``::

  aws route53 transfer-domain --region us-east-1 --cli-input-json file://C:\temp\transfer-domain.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Transferring Registration for a Domain to Amazon Route 53`_ in the *Amazon Route 53 Developer Guide*.

.. _`Transferring Registration for a Domain to Amazon Route 53`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-transfer-to-route-53.html

Use the following syntax for transfer-domain.json::

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
    "AuthCode": "string",
    "AutoRenew": boolean,
    "DomainName": "string",
    "DurationInYears": number,
    "IdnLangCode": "string",
    "Nameservers": [ 
      { 
        "GlueIps": [ "string" ],
        "Name": "string"
      }
    ],
    "PrivacyProtectAdminContact": boolean,
    "PrivacyProtectRegistrantContact": boolean,
    "PrivacyProtectTechContact": boolean,
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