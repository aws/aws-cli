**To publish a message to a topic**

The following ``publish`` command publishes the specified message to the specified SNS topic. ::

    aws sns publish \
        --topic-arn "arn:aws:sns:us-west-2:123456789012:my-topic" \
        --message file://message.txt

Contents of ``message.txt``::

    Hello World
    Second Line

Putting the message in a text file allows you to include line breaks.