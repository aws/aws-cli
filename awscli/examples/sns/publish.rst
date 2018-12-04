The following command publishes a message to an SNS topic named ``my-topic``::

  aws sns publish --topic-arn "arn:aws:sns:us-west-2:0123456789012:my-topic" --message file://message.txt

``message.txt`` is a text file containing the message to publish::

  Hello World
  Second Line

Putting the message in a text file allows you to include line breaks.