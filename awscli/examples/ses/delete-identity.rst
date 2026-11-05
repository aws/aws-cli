**To delete an identity**

The following ``delete-identity`` example deletes an identity from the list of identities verified with Amazon SES. ::

    aws ses delete-identity \
        --identity user@example.com

This command produces no output.

For more information, see `Verified identities in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html>`__ in the *Amazon Simple Email Service Developer Guide*.
