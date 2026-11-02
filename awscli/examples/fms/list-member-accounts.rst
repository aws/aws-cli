**To retrieve the member accounts in the organization**

The following ``list-member-accounts`` example lists all of the member accounts that are in the Firewall Manager administrator's organization. ::

    aws fms list-member-accounts

Output::

    {
        "MemberAccounts": [
            "123456789111",
            "123456789222",
            "123456789333"
        ]
    }

For more information, see `AWS Firewall Manager <https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
