**To create an SMS sandbox destination phone number**

The following ``create-sms-sandbox-phone-number`` example adds a destination phone number to your SMS sandbox. SNS sends a one-time password (OTP) to this number that you must verify before publishing SMS messages to it. ::

    aws sns create-sms-sandbox-phone-number \
        --phone-number "+12065550100" \
        --language-code en-US

This command produces no output.
