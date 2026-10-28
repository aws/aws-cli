**Example 1: To describe all policies associated with a load balancer**

The following ``describe-load-balancer-policies`` example describes all of the policies associated with the specified load balancer. ::

    aws elb describe-load-balancer-policies \
        --load-balancer-name my-load-balancer

Output::

    {
        "PolicyDescriptions": [
            {
                "PolicyAttributeDescriptions": [
                    {
                        "AttributeName": "ProxyProtocol",
                        "AttributeValue": "true"
                    }
                ],
                "PolicyName": "my-ProxyProtocol-policy",
                "PolicyTypeName": "ProxyProtocolPolicyType"
            },
            {
                "PolicyAttributeDescriptions": [
                    {
                        "AttributeName": "CookieName",
                        "AttributeValue": "my-app-cookie"
                    }
                ],
                "PolicyName": "my-app-cookie-policy",
                "PolicyTypeName": "AppCookieStickinessPolicyType"
            },
            {
                "PolicyAttributeDescriptions": [
                    {
                        "AttributeName": "CookieExpirationPeriod",
                        "AttributeValue": "60"
                    }
                ],
                "PolicyName": "my-duration-cookie-policy",
                "PolicyTypeName": "LBCookieStickinessPolicyType"
            },
            .
            .
            .
        ]
    }

**Example 2: To describe a specific policy associated with a load balancer**

The following ``describe-load-balancer-policies`` example describes the specified policy associated with the specified load balancer. ::

    aws elb describe-load-balancer-policies \
        --load-balancer-name my-load-balancer \
        --policy-name my-authentication-policy

Output::

    {
        "PolicyDescriptions": [
            {
                "PolicyAttributeDescriptions": [
                    {
                        "AttributeName": "PublicKeyPolicyName",
                        "AttributeValue": "my-PublicKey-policy"
                    }
                ],
                "PolicyName": "my-authentication-policy",
                "PolicyTypeName": "BackendServerAuthenticationPolicyType"
            }
        ]
    }
