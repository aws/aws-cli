**To update a filter**

The following ``update-filter`` example updates a filter to omit Lambda findings instead of ECR instance findings. ::

    aws inspector2 update-filter \
        --filter-arn "arn:aws:inspector2:us-west-2:123456789012:owner/o-EXAMPLE222/filter/EXAMPLE444444444" \
        --name "ExampleSuppressionRuleLambda" \
        --description "This suppression rule omits Lambda instance findings" \
        --reason "Updating filter to omit Lambda instance findings instead of ECR instance findings"

Output::

    {
        "arn": "arn:aws:inspector2:us-west-2:123456789012:owner/o-EXAMPLE222/filter/EXAMPLE444444444"
    }

For more information, see `Managing findings in Amazon Inspector <https://docs.aws.amazon.com/inspector/latest/user/findings-managing.html>`__ in the *Amazon Inspector User Guide*.