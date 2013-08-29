**To delete an identity**

The following example uses the ``delete-identity`` command to delete an identity from the list of identities verified with Amazon SES::

    aws ses delete-identity --identity user@example.com

Output::

 {
    "ResponseMetadata": {
        "RequestId": "8943f630-d479-11e2-a86e-5dc1b5a3e4bb"
    }
 }


For more information about verified identities, see `Verifying Email Addresses and Domains in Amazon SES`_ in the *Amazon Simple Email Service Developer Guide*.

.. _`Verifying Email Addresses and Domains in Amazon SES`: http://docs.aws.amazon.com/ses/latest/DeveloperGuide/verify-addresses-and-domains.html
