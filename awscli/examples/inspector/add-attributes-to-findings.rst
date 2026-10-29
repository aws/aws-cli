**To add attributes to findings**

The following ``add-attributes-to-findings`` example assigns an attribute with the key of ``Example`` and value of ``example`` to the finding with the ARN of ``arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-8l1VIE0D/run/0-Z02cjjug/finding/0-T8yM9mEU``. ::

    aws inspector add-attributes-to-findings \
        --finding-arns arn:aws:inspector:us-west-2:123456789012:target/0-0kFIPusq/template/0-8l1VIE0D/run/0-Z02cjjug/finding/0-T8yM9mEU \
        --attributes key=Example,value=example

Output::

    {
        "failedItems": {}
    }

