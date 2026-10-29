**To update the privacy settings for the contacts for a domain**

The following ``update-domain-contact-privacy`` example turns off privacy protection for the administrative contact for the example.com domain. This command runs only in the ``us-east-1`` Region. 

If your default region is set to ``us-east-1``, you can omit the ``region`` parameter. ::

    aws route53domains update-domain-contact-privacy \
        --region us-east-1 \
        --domain-name example.com \
        --no-admin-privacy

Output::

    {
        "OperationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

To confirm that the operation succeeded, you can run ``get-operation-detail``. For more information, see `get-operation-detail <https://docs.aws.amazon.com/cli/latest/reference/route53domains/get-operation-detail.html>`__ . 

For more information, see `Enabling or Disabling Privacy Protection for Contact Information for a Domain <https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-privacy-protection.html>`__ in the *Amazon Route 53 Developer Guide*.
