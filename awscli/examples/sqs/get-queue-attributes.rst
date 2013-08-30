**To retrieve queue attributes from an SQS queue**

The following ``get-queue-attributes`` command retrieves the queue ARN::

  aws sqs get-queue-attributes --queue-url https://queue.amazonaws.com/803981987763/MyQueue --attribute-names QueueArn

The following ``get-queue-attributes`` command retrieves multiple attributes from the specified SQS queue::

  aws sqs get-queue-attributes --queue-url https://queue.amazonaws.com/803981987763/MyQueue --attribute-names QueueArn MaximumMessageSize VisibilityTimeout

For more information, see `Using the AWS Command Line Interface with Amazon SQS and Amazon SNS`_ in the *AWS Command Line Interface User Guide*.

.. _`Using the AWS Command Line Interface with Amazon SQS and Amazon SNS`: http://docs.aws.amazon.com/cli/latest/userguide/cli-sqs-queue-sns-topic.html

