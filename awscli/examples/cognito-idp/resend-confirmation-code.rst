**To force a password change**

This example sends a message to jane@example.com to change their password.

Command::

  aws cognito-idp resend-confirmation-code --client-id 38fjsnc484p94kpqsnet7mpld0 --username jane@example.com

Output::

  {
    "CodeDeliveryDetails": {
        "Destination": "j***@e***.com",
        "DeliveryMedium": "EMAIL",
        "AttributeName": "email"
    }
  }