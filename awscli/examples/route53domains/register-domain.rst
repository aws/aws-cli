**To register a domain**

The following ``register-domain`` command registers a domain using the settings in the JSON-formatted file ``C:\temp\register-domain.json``::

  aws route53 register-domain --region us-east-1 --cli-input-json file://C:\temp\register-domain.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Registering a New Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Registering a New Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html

For information about which top-level domains (TLDs) require values for ``ExtraParams`` and what the valid values are, see `ExtraParam`_ in the *Amazon Route 53 API Reference*.

.. _`ExtraParam`: https://docs.aws.amazon.com/Route53/latest/APIReference/API_domains_ExtraParam.html
  
Use the following syntax for register-domain.json::

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
    "AutoRenew": boolean,
    "DomainName": "string",
    "DurationInYears": number,
    "IdnLangCode": "string",
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