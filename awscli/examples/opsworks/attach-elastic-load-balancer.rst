**To attach a load balancer to a layer**

The following example attaches a load balancer, identified by its name, to a specified layer. ::

  aws opsworks --region us-east-1 attach-elastic-load-balancer --elastic-load-balancer-name Java-LB --layer-id 888c5645-09a5-4d0e-95a8-812ef1db76a4 

**Note**: AWS OpsWorks CLI commands should set the region to ``us-east-1`` regardless of the stack's location.

*Output*: None.

**More Information**

For more information, see `Elastic Load Balancing`_ in the *AWS OpsWorks User Guide*.

.. _`Elastic Load Balancing`: http://docs.aws.amazon.com/opsworks/latest/userguide/load-balancer-elb.html

