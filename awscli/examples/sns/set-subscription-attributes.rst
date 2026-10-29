**To set subscription attributes**

The following ``set-subscription-attributes`` example sets the ``RawMessageDelivery`` attribute to an SQS subscription. ::

    aws sns set-subscription-attributes \
        --subscription-arn arn:aws:sns:us-east-1:123456789012:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc \
        --attribute-name RawMessageDelivery \
        --attribute-value true
  
This command produces no output.

For more information, see `Amazon SNS raw message delivery <https://docs.aws.amazon.com/sns/latest/dg/sns-large-payload-raw-message-delivery.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

The following ``set-subscription-attributes`` example sets a ``FilterPolicy`` attribute to an SQS subscription. ::

    aws sns set-subscription-attributes \
        --subscription-arn arn:aws:sns:us-east-1:123456789012:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc \
        --attribute-name FilterPolicy \
        --attribute-value "{ \"anyMandatoryKey\": [\"any\", \"of\", \"these\"] }"

This command produces no output.

For more information, see `Amazon SNS subscription filter policies <https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html>`__ in the *Amazon Simple Notification Service Developer Guide*.

The following ``set-subscription-attributes`` example removes the ``FilterPolicy`` attribute from an SQS subscription. ::

    aws sns set-subscription-attributes \
        --subscription-arn arn:aws:sns:us-east-1:123456789012:mytopic:f248de18-2cf6-578c-8592-b6f1eaa877dc \
        --attribute-name FilterPolicy \
        --attribute-value "{}"

This command produces no output.

For more information, see `Amazon SNS subscription filter policies <https://docs.aws.amazon.com/sns/latest/dg/sns-subscription-filter-policies.html>`__ in the *Amazon Simple Notification Service Developer Guide*.
