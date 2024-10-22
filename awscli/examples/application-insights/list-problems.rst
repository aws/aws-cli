**To list all problems identified in an application**

This example uses the ``list-problems`` command to list all the identified problems in an applicaiton. ::

    aws application-insights list-problems \
        --resource-group-name MYEC2

Output::

    {
        "ProblemList": [{
            "Id": "p-1aaaf123-abc4-5678-a12e-d01234e56d7e",
            "Title": "EC2: High CPU",
            "Insights": "High CPU on the .NET application layer. This can result in application performance degradation due to high load on web servers, or application errors. If you experience high load conditions for long periods of time, use AWS Auto Scaling to add additional resources to process the load. To troubleshoot, collect a full user dump with task manager on the high CPU process and collect PerfMon logs with the thread counter to identify the thread ID causing high CPU.",
            "Status": "PENDING",
            "AffectedResource": "arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56",
            "StartTime": "2024-05-01T08:05:55.432000+00:00",
            "EndTime": "1970-01-01T00:00:00+00:00",
            "SeverityLevel": "Medium",
            "AccountId": "123456789012",
            "ResourceGroupName": "MYEC2",
            "Feedback": {
                "INSIGHTS_FEEDBACK": "NOT_SPECIFIED"
            },
            "RecurringCount": 0,
            "Visibility": "VISIBLE",
            "ResolutionMethod": "UNRESOLVED"
        }],
        "ResourceGroupName": "MYEC2",
        "AccountId": "123456789012"
    }