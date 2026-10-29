**To delete a platform application**

The following ``delete-platform-application`` example deletes the specified platform application. ::

    aws sns delete-platform-application \
        --platform-application-arn arn:aws:sns:us-west-2:123456789012:app/ADM/MyApplication

This command produces no output.

For more information, see `Creating an Amazon SNS platform application <https://docs.aws.amazon.com/sns/latest/dg/mobile-push-send-register.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
