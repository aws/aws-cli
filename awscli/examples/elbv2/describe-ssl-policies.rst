**To describe a policy used for SSL negotiation**

This example describes the specified policy used for SSL negotiation.

Command::

  aws elbv2 describe-ssl-policies --names ELBSecurityPolicy-2015-05
      
Output::

  {
    "SslPolicies": [
        {
            "SslProtocols": [
                "TLSv1",
                "TLSv1.1",
                "TLSv1.2"
            ],
            "Ciphers": [
                {
                    "Priority": 1,
                    "Name": "ECDHE-ECDSA-AES128-GCM-SHA256"
                },
                {
                    "Priority": 2,
                    "Name": "ECDHE-RSA-AES128-GCM-SHA256"
                },
                {
                    "Priority": 3,
                    "Name": "ECDHE-ECDSA-AES128-SHA256"
                },

                ...

                {
                    "Priority": 19,
                    "Name": "AES256-SHA"
                }
            ],
            "Name": "ELBSecurityPolicy-2015-05"
        }
    ]
  }

**To describe all policies used for SSL negotiation**

This example describes all the policies that you can use for SSL negotiation.

Command::

  aws elbv2 describe-ssl-policies
