**To update a web ACL**

The following ``update-web-acl`` example changes settings for an existing web ACL. This call requires an ID, which you can obtain from the call, ``list-web-acls``, and a lock token and other settings, which you can obtain from the call ``get-web-acl``. This call also returns a lock token that you can use for a subsequent update. ::

    aws wafv2 update-web-acl \
        --name TestWebAcl \
        --scope REGIONAL \
        --id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --lock-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --default-action Block={} \
        --visibility-config SampledRequestsEnabled=false,CloudWatchMetricsEnabled=false,MetricName=NewMetricTestWebAcl \
        --rules file://waf-rule.json

Contents of ``waf-rule.json``::

    [
        {
            "Name": "basic-rule",
            "Priority": 0,
            "Statement": {
                "AndStatement": {
                    "Statements": [
                        {
                            "ByteMatchStatement": {
                                "SearchString": "example.com",
                                "FieldToMatch": {
                                    "SingleHeader": {
                                        "Name": "host"
                                    }
                                },
                                "TextTransformations": [
                                    {
                                        "Priority": 0,
                                        "Type": "LOWERCASE"
                                    }
                                ],
                                "PositionalConstraint": "EXACTLY"
                            }
                        },
                        {
                            "GeoMatchStatement": {
                                "CountryCodes": [
                                    "US",
                                    "IN"
                                ]
                            }
                        }
                    ]
                }
            },
            "Action": {
                "Allow": {}
            },
            "VisibilityConfig": {
                "SampledRequestsEnabled": true,
                "CloudWatchMetricsEnabled": true,
                "MetricName": "basic-rule"
            }
        }
    ]

Output::

    {
        "NextLockToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
    }

For more information, see `Managing and Using a Web Access Control List (Web ACL) <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.