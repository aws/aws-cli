**To create an SQS queue**

The following ``create-queue`` command creates an SQS queue named my-queue::

  aws sqs create-queue --queue-name my-queue

**To create an SQS queue with a Redrive Policy**

The following command creates an SWS queue with attributes loaded from a JSON file::

  aws sqs create-queue --queue-name my-queue --attributes file://attributes.json

attributes.json::

  {
    "RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-west-2:0123456789012:deadletter\", \"maxReceiveCount\":\"5\"}"
  }

Because the value of the RedrivePolicy key is a JSON document, you must escape its quotes and provide the attributes parameter in JSON.

For more information about using SQS with the AWS CLI, see `Using the AWS Command Line Interface with Amazon SQS and Amazon SNS`_ in the *AWS Command Line Interface User Guide*.

.. _`Using the AWS Command Line Interface with Amazon SQS and Amazon SNS`: http://docs.aws.amazon.com/cli/latest/userguide/cli-sqs-queue-sns-topic.html

