**To create a dashboard**

The following ``put-dashboard`` example creates a dashboard named ``Dashboard-A`` in the specified account. ::

    aws cloudwatch put-dashboard \
        --dashboard-name Dashboard-A \
        --dashboard-body "{\"widgets\":[{\"type\":\"metric\",\"x\":0,\"y\":0,\"width\":6,\"height\":6,\"properties\":{\"view\":\"timeSeries\",\"stacked\":false,\"metrics\":[[\"Namespace\",\"CPUUtilization\",\"Environment\",\"Prod\",\"Type\",\"App\"]],\"region\":\"us-east-1\"}}]}"

Output::

    {
        "DashboardValidationMessages": []
    }
    
For more information, see `Creating a CloudWatch dashboard <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create_dashboard.html>`__ in the *Amazon CloudWatch User Guide*.