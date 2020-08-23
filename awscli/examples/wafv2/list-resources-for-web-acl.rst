**To retrieve the resources associated with a web ACL**

The following ``list-resources-for-web-acl`` retrieves all resources that are currently associated with the specified web ACL in the region ``us-west-2``. ::

    aws wafv2 list-resources-for-web-acl \
        --web-acl-arn arn:aws:wafv2:us-west-2:123456789012:regional/webacl/TestWebAcl/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --region us-west-2

Output::

    {
        "ResourceArns":[
            "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/waf-cli-alb/1ea17125f8b25a2a"
        ]
    } 

For more information, see `Associating or Disassociating a Web ACL with an AWS Resource <https://docs.aws.amazon.com/waf/latest/developerguide/web-acl-associating-aws-resource.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
