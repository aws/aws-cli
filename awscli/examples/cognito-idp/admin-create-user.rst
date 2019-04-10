**To create a user**

This example creates a user with username diego. An email address and phone
number are specified. 

Command::

  aws cognito-idp admin-create-user --user-pool-id us-west-2_aaaaaaaaa --username diego --user-attributes Name=email,Value=diego@example.com Name=phone_number,Value="+15555551212" --message-action SUPPRESS

Output::

  {
      "User": {
          "Username": "diego",
          "Attributes": [
              {
                  "Name": "sub",
                  "Value": "b72840b1-9a77-4988-b559-5e7406a1afe9"
              },
              {
                  "Name": "phone_number",
                  "Value": "+15555551212"
              },
              {
                  "Name": "email",
                  "Value": "diego@example.com"
              }
          ],
          "UserCreateDate": 1554857988.118,
          "UserLastModifiedDate": 1554857988.118,
          "Enabled": true,
          "UserStatus": "FORCE_CHANGE_PASSWORD"
      }
  }

