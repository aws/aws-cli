**To initiate authorization**

This example initiates authorization using the ADMIN_NO_SRP_AUTH flow for username jane@example.com

The client must have sign-in API for server-based authentication (ADMIN_NO_SRP_AUTH) enabled.

Use the session information in the return value to call ''admin-respond-to-auth-challenge''.

Command::

  aws cognito-idp admin-initiate-auth --user-pool-id us-west-1_111111111 --client-id 3n4b5urk1ft4fl3mg5e62d9ado --auth-flow ADMIN_NO_SRP_AUTH --auth-parameters USERNAME=jane@example.com,PASSWORD=password
  
Output::

  {
    "ChallengeName": "NEW_PASSWORD_REQUIRED",
    "Session": "rXKDTDNwK2qXehKc-TdvROgbjGvWOKIQNxV72oSLEr5Ais3csyaYgaofbM0f-GLIBQ0Xv16VOPJe9aqPfujUVMot7K5jmysx3TuF2bTE0GYxfR2T9gf-dX9g3soOs1fZavVGkubVUqdD3fruBCmQGEQ9ziiprVWK10ZlHQBuMsw-glUd1L72-v1mXCV5uwYNwGve3wMg4mEQpr0UODo6t9pzcpwpK_tVLpMk10c1EP61k7VWMT7Iqc2Tf-S9OL-cW5DMiqdTDZA0Y4S53p0Jbm7UHYZLuH8JFhO1e3NTnbIRhX3AMtRv7RU8gqtVj1J7DM5nE94Uzexu__Wm-PX9AEdbJx-0QgKbn1o4EgufHs4AcqTnEew-bN4rBAsS02S8TrCG8eR6kT7yDc7DGJyFc1JKje2qmDSHuEGYt-8Jx_fJU3QoOMjaqM-7uayFZK-ZN3BWEGo5k-vIZQyTPUEzV5RNqOTjToGkZsbM5XNX2RZvplwAOGBX6XYji1XYilCy2nJ6dRFge7vKaPYsHqQf9lGTYtfxFYGUQfu6MDdgc9vw5cD9CJxMTmDadDCabqD4RswQumLosoXiIQ6Q7z9IaBleszejOtfVCBw3fcagoX20jbYJgOSJET-BKdnJu6yu9pKgbqBxSOG9ZgU-Yjh_DpLli7J7qDO50qpxOD1P3oNC9JSHegtoMiUdQK5px8No1vAlCoMY9xIEcTFnIRCGkEhreD1yZiAKMB2LPro06TkzmWz4qI879Xzdacs9h-kAFQGtKMydHu1rzoBWhksX_5bunwilpXwP213dj6cDa-c9iEDSwHZ6erwXJU2-sHd-XKM_P5i-a-JCGa0vsSwBLH2QcxUv0uBhT34tCz9QiOuXqI7JG58td_f4vNiAxWxQgMbu915huC8",
    "ChallengeParameters": {
        "USER_ID_FOR_SRP": "84514837-dcbc-4af1-abff-f3c109334894",
        "requiredAttributes": "[]",
        "userAttributes": "{\"email_verified\":\"true\",\"phone_number_verified\":\"true\",\"phone_number\":\"+01xxx5550100\",\"email\":\"jane@example.com\"}"
    }
  }