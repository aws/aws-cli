**To purchase a Reserved Instance offering**

The following ``purchase-reserved-instances-offering`` example purchases a Reserved Instances offering, specifying an offering ID and instance count. ::

    aws ec2 purchase-reserved-instances-offering \
        --reserved-instances-offering-id ec06327e-dd07-46ee-9398-75b5fexample \
        --instance-count 3


Output::

    {
        "ReservedInstancesId": "af9f760e-6f91-4559-85f7-4980eexample"
    }

For more information, see `Buy Reserved Instances for Amazon EC2 <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html>`__ in the *Amazon EC2 User Guide*.
