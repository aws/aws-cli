**To enable or disable Easy DKIM for an Amazon SES verified identity**

The following ``set-identity-dkim-enabled`` example disables DKIM for a verified email address. ::

    aws ses set-identity-dkim-enabled \
        --identity user@example.com \
        --no-dkim-enabled

This command produces no output.

For more information, see `Easy DKIM in Amazon SES <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dkim-easy.html>`__ in the *Amazon Simple Email Service Developer Guide*.
