**To register an EC2 instance**

The following ``register`` command registers the existing EC2 instance
``i-12345678`` into the given stack::

  aws opsworks register --infrastructure-class=ec2 --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb i-12345678

A username and SSH key file may be specified using the ``--ssh-username`` and
``--ssh-private-key`` options, e.g.::

  aws opsworks register --infrastructure-class=ec2 --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb --ssh-username admin --ssh-private-key ssh_private_key i-12345678

**To register the local instance**

The following ``import`` command imports the EC2 instance the AWS CLI is
running on into the given stack::

  aws opsworks register --infrastructure-class=ec2 --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb --local

**To register an on-premises machine**

The following ``register`` command registers an existing machine reachable
using the IP address ``192.0.2.3`` and registers it with the given stack::

  aws opsworks register --infrastructure-class=on-premises --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb 192.0.2.3

**To register an on-premises machine using extra options**

The following ``register`` command registers an existing machine reachable
using the name ``host1`` and registers it with the given stack. Additionally,
``1.2.3.4`` is used as the public IP address and ``10.0.0.2`` is used as the
private IP address. OpsWorks will also use the host name ``webserver1``::

  aws opsworks register --infrastructure-class=on-premises --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb --override-hostname webserver1 --override-public-ip 1.2.3.4 --override-private-ip 10.0.0.2 host1

A username and SSH key file may be specified using the ``--ssh-username`` and
``--ssh-private-key`` options, e.g.::

  aws opsworks register --infrastructure-class=on-premises --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb --ssh-username admin --ssh-private-key ssh_private_key 192.0.2.3

**To register the local machine**

In order to register the local machine instead of a remote one, the
``register`` command may be called with the ``--local`` option instead of a
host name or IP address. For example::

  aws opsworks register --infrastructure-class=on-premises --stack-id 935450cc-61e0-4b03-a3e0-160ac817d2bb --local
