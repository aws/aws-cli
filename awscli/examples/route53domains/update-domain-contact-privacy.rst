**To update the privacy settings for the contacts for a domain**

The following ``update-domain-contact-privacy`` command updates privacy protection for contact information for a domain using the settings in the JSON-formatted file ``C:\temp\update-domain-contact-privacy.json``::

  aws route53 update-domain-contact-privacy --region us-east-1 --cli-input-json file://C:\temp\update-domain-contact-privacy.json

If the default region is us-east-1, you can omit the ``region`` parameter.

For more information, see `Enabling or Disabling Privacy Protection for Contact Information for a Domain`_ in the *Amazon Route 53 Developer Guide*.

.. _`Enabling or Disabling Privacy Protection for Contact Information for a Domain`: http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-privacy-protection.html

Use the following syntax for update-domain-contact-privacy.json::

  {
    "AdminPrivacy": boolean,
    "DomainName": "string",
    "RegistrantPrivacy": boolean,
    "TechPrivacy": boolean
  }