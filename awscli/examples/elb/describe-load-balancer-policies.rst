**To describe all the policies associated with a load balancer**

This example describes all the policies associated with a specified load balancer.

Command::

  aws elb describe-load-balancer-policies --load-balancer-name MyLoadBalancer

Output::

  {
    "PolicyDescriptions": [
      {
        "PolicyAttributeDescriptions": [
          {
            "AttributeName": "CookieExpirationPeriod",
            "AttributeValue": "60"
          }
        ],
        "PolicyName": "MyDurationStickyPolicy",
        "PolicyTypeName": "LBCookieStickinessPolicyType"
      },
      {
        "PolicyAttributeDescriptions": [
          {
            "AttributeName": "ProxyProtocol",
            "AttributeValue": "True"
          }
        ],
        "PolicyName": "EnableProxyProtocol",
        "PolicyTypeName": "ProxyProtocolPolicyType"
      },
      {
        "PolicyAttributeDescriptions": [
          {
            "AttributeName": "CookieName",
            "AttributeValue": "MyAppCookie"
          }
        ],
        "PolicyName": "MyAppStickyPolicy",
        "PolicyTypeName": "AppCookieStickinessPolicyType"
      }
    ]
  }

**To describe a specified policy associated with a load balancer**

This example describes a specified policy associated with a specified load balancer.

Command::

  aws elb describe-load-balancer-policies --load-balancer-name MyLoadBalancer  --policy-name MyDurationStickyPolicy

Output::

  {
    "PolicyDescriptions": [
      {
        "PolicyAttributeDescriptions": [
          {
            "AttributeName": "CookieExpirationPeriod",
            "AttributeValue": "60"
          }
        ],
        "PolicyName": "MyDurationStickyPolicy",
        "PolicyTypeName": "LBCookieStickinessPolicyType"
      }
    ]
  }

