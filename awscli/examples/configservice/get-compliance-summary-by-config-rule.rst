**To get the compliance summary for your AWS Config rules**

The following ``get-compliance-summary-by-config-rule`` example returns the number of rules that are compliant and the number that are noncompliant. ::

    aws configservice get-compliance-summary-by-config-rule

In the output, the value for each ``CappedCount`` attribute indicates how many rules are compliant or noncompliant.

Output::

    {
        "ComplianceSummary": {
            "NonCompliantResourceCount": {
                "CappedCount": 3,
                "CapExceeded": false
            },
            "ComplianceSummaryTimestamp": 1452204131.493,
            "CompliantResourceCount": {
                "CappedCount": 2,
                "CapExceeded": false
            }
        }
    }

For more information, see `Viewing Compliance Information and Evaluation Results for your AWS Resources with AWS Config <https://docs.aws.amazon.com/config/latest/developerguide/evaluate-config_view-compliance.html>`__ in the *AWS Config Developer Guide*.
