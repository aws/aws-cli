**To check whether an event pattern matches a specified event**

The following ``test-event-pattern`` example tests whether the pattern ``source:com.mycompany.myapp`` matches the specified event. In this example, the output would be ``true``. ::

    aws events test-event-pattern \
        --event-pattern "{\"source\":[\"com.mycompany.myapp\"]}" \
        --event "{\"id\":\"1\",\"source\":\"com.mycompany.myapp\",\"detail-type\":\"myDetailType\",\"account\":\"123456789012\",\"region\":\"us-west-2\",\"time\":\"2017-04-11T20:11:04Z\"}"

Output::

    {
        "Result": true
    }

For more information, see `Amazon EventBridge event patterns <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html>`__ in the *Amazon EventBridge User Guide*.
