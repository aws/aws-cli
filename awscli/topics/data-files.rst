:title: AWS Service Data Files
:description: How data files describing AWS services are located
:category: General

The AWS CLI uses data files from botocore for a majority of its functionality.
This can include

    * Service models (e.g. the model for EC2, S3, DynamoDB, etc.)
    * Service model extras which customize the service models
    * Other models associated with a service (pagination, waiters)
    * Non service-specific config (Endpoint data, retry config)

Loading a module is broken down into several steps:

    * Determining the path to load
    * Search the ``data_path`` for files to load
    * The mechanics of loading the file
    * Searching for extras and applying them to the loaded file

The last item is used so that other faster loading mechanism
besides the default JSON loader can be used.

Search Path
===========

In terms of precedence the data directory is located using the following
methods:

1. ``set_config_variable`` on a botocore session (botocore code side)
2. ``AWS_DATA_PATH`` environment variable, which is separated using the OS path
   separator ( ':' for POSIX or ';' for Windows )
3. `~/.aws/models` directory
4. The botocore built in data directory ``<botocore root>/data/``

Directory Layout
================

The Loader expects a particular directory layout.  In order for any
directory specified in ``AWS_DATA_PATH`` to be considered, it must have
this structure for service models::

    <root>
      |
      |-- servicename1
      |   |-- 2012-10-25
      |       |-- service-2.json
      |-- ec2
      |   |-- 2014-01-01
      |   |   |-- paginators-1.json
      |   |   |-- service-2.json
      |   |   |-- waiters-2.json
      |   |-- 2015-03-01
      |       |-- paginators-1.json
      |       |-- service-2.json
      |       |-- waiters-2.json
      |       |-- service-2.sdk-extras.json


That is:

    * The root directory contains sub directories that are the name
      of the services.
    * Within each service directory, there's a sub directory for each
      available API version.
    * Within each API version, there are model specific files, including
      (but not limited to): ``service-2.json``, ``waiters-2.json``,
      ``paginators-1.json``

The ``-1`` and ``-2`` suffix at the end of the model files denote which version
schema is used within the model.  Even though this information is available in
the ``version`` key within the model, this version is also part of the filename
so that code does not need to load the JSON model in order to determine which
version to use.

The ``sdk-extras`` and similar files represent extra data that needs to be
applied to the model after it is loaded. Data in these files might represent
information that doesn't quite fit in the original models, but is still needed
for the sdk. For instance, additional operation parameters might be added here
which don't represent the actual service api.
"""
