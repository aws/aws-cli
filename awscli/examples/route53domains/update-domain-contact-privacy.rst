**To update the privacy settings for the contacts for a domain**

The following ``update-domain-contact-privacy`` command turns off privacy protection for the administrative contact for the example.com domain. ::

    aws route53domains update-domain-contact-privacy \
        --domain-name example.com \
        --no-admin-privacy

Output::

    {
        "OperationId": "b3a219e9-d801-4244-b533-b7256example"
    }

To confirm that the operation succeeded, you can run ``get-operation-detail``. For more information, see `get-operation-detail <https://docs.aws.amazon.com/cli/latest/reference/route53domains/get-operation-detail.html>`__ . 

For more information, see `Enabling or Disabling Privacy Protection for Contact Information for a Domain <http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-privacy-protection.html>`__ in the *Amazon Route 53 Developer Guide*.
