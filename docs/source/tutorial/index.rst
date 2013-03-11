*****************************
Getting Started With botocore
*****************************

The ``botocore`` package provides a low-level interface to Amazon
services.  It is responsible for:

* Providing access to all available services
* Providing access to all operations within a service
* Marshaling all parameters for a particular operation in the correct format
* Signing the request with the correct authentication signature
* Receiving the response and returning the data in native Python data structures

``botocore`` does not provide higher-level abstractions on top of these
services, operations and responses.  That is left to the application
layer.  The goal of ``botocore`` is to handle all of the low-level details
of making requests and getting results from a service.

The ``botocore`` package is mainly data-driven.  Each service has a JSON
description which specifies all of the operations the service supports,
all of the parameters the operation accepts, all of the documentation
related to the service, information about supported regions and endpoints, etc.
Because this data can be updated quickly based on the canonical description
of these services, it's much easier to keep ``botocore`` current.

Some examples:

.. toctree::
   :maxdepth: 2

   ec2_examples
   s3_streaming_output
   s3_streaming_input
