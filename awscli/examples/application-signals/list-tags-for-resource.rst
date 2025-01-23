**To display the tags associated with a CloudWatch resource**

The following ``list-tags-for-resource`` example displays the tags associated with a CloudWatch resource. ::

    aws application-signals list-services \
        --start-time 1734918791 \
        --end-time 1734965591

Output::

    {
        "Tags": [{
            "Key": "test",
            "Value": "value"
        }]
    }

For more information, see `<https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html>`__ in the *Amazon CloudWatch User Guide*.