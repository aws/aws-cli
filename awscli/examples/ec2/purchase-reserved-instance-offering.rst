**To purchase a Reserved Instance offering**

The following ``purchase-reserved-instances-offering`` example command purchases a Reserved Instances offering, specifying an offering ID and instance count. ::

    aws ec2 purchase-reserved-instances-offering \
        --reserved-instances-offering-id ec06327e-dd07-46ee-9398-75b5fexample \
        --instance-count 3
  
Output::

    {
        "ReservedInstancesId": "af9f760e-6f91-4559-85f7-4980eexample"
    }

By default, the purchase is completed immediately. Alternatively, to queue the purchase until a specified time, add the following parameter to the previous call. ::

    --purchase-time "2020-12-01T00:00:00Z"
