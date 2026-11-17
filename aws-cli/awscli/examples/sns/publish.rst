**Example 1: To publish a message to a topic**

The following ``publish`` example publishes the specified message to the specified SNS topic. The message comes from a text file, which enables you to include line breaks. ::

    aws sns publish \
        --topic-arn "arn:aws:sns:us-west-2:123456789012:my-topic" \
        --message file://message.txt

Contents of ``message.txt``::

    Hello World
    Second Line

Output::

    {
        "MessageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Publishing an Amazon SNS message <https://docs.aws.amazon.com/sns/latest/dg/sns-publishing.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

**Example 2: To publish an SMS message to a phone number**

The following ``publish`` example publishes the message ``Hello world!`` to the phone number ``+1-555-555-0100``. ::

    aws sns publish \
        --message "Hello world!" \
        --phone-number +1-555-555-0100

Output::

    {
        "MessageId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Sending SMS messages using Amazon SNS <https://docs.aws.amazon.com/sns/latest/dg/sms_sending-overview.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
