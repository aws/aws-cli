**To renew a domain**

The following ``renew-domain`` command renews a domain using the settings in the JSON-formatted file ``C:\temp\renew-domain.json``::

  aws route53 renew-domain --region us-east-1 --cli-input-json file://C:\temp\renew-domain.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Renewing Registration for a Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Renewing Registration for a Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-renew.html

For information about the maximum renewal period for the domain, see the "Registration and Renewal Period" section for your top-level domain (TLD) in the section `Domains That You Can Register with Amazon Route 53`_ in the *Amazon Route 53 API Reference*.

.. _`Domains That You Can Register with Amazon Route 53`: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/registrar-tld-list.html
  
Use the following syntax for renew-domain.json::

  {
    "CurrentExpiryYear": number,
    "DomainName": "string",
    "DurationInYears": number
  }
  
To get the value for ``CurrentExpiryYear``, use the ``get-domain-detail`` command.