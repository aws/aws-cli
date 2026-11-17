**To validate configuration settings**

The following ``validate-configuration-settings`` example validates a CloudWatch custom metrics config document. ::

    aws elasticbeanstalk validate-configuration-settings \
        --application-name my-app \
        --environment-name my-env \
        --option-settings file://options.json

Contents of ``options.json``::

    [
        {
            "Namespace": "aws:elasticbeanstalk:healthreporting:system",
            "OptionName": "ConfigDocument",
            "Value": "{\"CloudWatchMetrics\": {\"Environment\": {\"ApplicationLatencyP99.9\": null,\"InstancesSevere\": 60,\"ApplicationLatencyP90\": 60,\"ApplicationLatencyP99\": null,\"ApplicationLatencyP95\": 60,\"InstancesUnknown\": 60,\"ApplicationLatencyP85\": 60,\"InstancesInfo\": null,\"ApplicationRequests2xx\": null,\"InstancesDegraded\": null,\"InstancesWarning\": 60,\"ApplicationLatencyP50\": 60,\"ApplicationRequestsTotal\": null,\"InstancesNoData\": null,\"InstancesPending\": 60,\"ApplicationLatencyP10\": null,\"ApplicationRequests5xx\": null,\"ApplicationLatencyP75\": null,\"InstancesOk\": 60,\"ApplicationRequests3xx\": null,\"ApplicationRequests4xx\": null},\"Instance\": {\"ApplicationLatencyP99.9\": null,\"ApplicationLatencyP90\": 60,\"ApplicationLatencyP99\": null,\"ApplicationLatencyP95\": null,\"ApplicationLatencyP85\": null,\"CPUUser\": 60,\"ApplicationRequests2xx\": null,\"CPUIdle\": null,\"ApplicationLatencyP50\": null,\"ApplicationRequestsTotal\": 60,\"RootFilesystemUtil\": null,\"LoadAverage1min\": null,\"CPUIrq\": null,\"CPUNice\": 60,\"CPUIowait\": 60,\"ApplicationLatencyP10\": null,\"LoadAverage5min\": null,\"ApplicationRequests5xx\": null,\"ApplicationLatencyP75\": 60,\"CPUSystem\": 60,\"ApplicationRequests3xx\": 60,\"ApplicationRequests4xx\": null,\"InstanceHealth\": null,\"CPUSoftirq\": 60}},\"Version\": 1}"
        }
    ]

If the options that you specify are valid for the specified environment, Elastic Beanstalk returns an empty Messages array.

Output::

    {
        "Messages": []
    }

If validation fails, the response will include information about the error.

Output::

    {
        "Messages": [
            {
                "OptionName": "ConfigDocumet",
                "Message": "Invalid option specification (Namespace: 'aws:elasticbeanstalk:healthreporting:system', OptionName: 'ConfigDocumet'): Unknown configuration setting.",
                "Namespace": "aws:elasticbeanstalk:healthreporting:system",
                "Severity": "error"
            }
        ]
    }

For more information about namespaces and supported options, see `Configuration options <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html>`__ in the *AWS Elastic Beanstalk Developer Guide*.
