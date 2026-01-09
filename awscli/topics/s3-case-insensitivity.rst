:title: AWS CLI S3 Case-Insensitivity
:description: Using 'aws s3' commands on case-insensitive filesystems
:category: S3
:related command: s3 cp, s3 sync, s3 mv


This page explains how to detect and handle potential case conflicts when
downloading multiple objects from S3 to a local case-insensitive filesystem
using a single AWS CLI command.

Case conflicts
==============
S3 object keys are case-sensitive meaning that a bucket can have a set of
key names that differ only by case, for example, ``a.txt`` and ``A.txt``.

The AWS CLI offers high-level S3 commands that manage transfers of
multiple S3 objects using a single command:

* ``aws s3 sync``
* ``aws s3 cp --recursive``
* ``aws s3 mv --recursive``

Case conflicts can occur on case-insensitive filesystems when an S3 bucket
has multiple objects whose keys differ only by case and a single AWS CLI
command is called to download multiple S3 objects **OR** a local file
already exists whose name differs only by case.

For example, consider an S3 bucket with the following stored objects:

* ``a.txt``
* ``A.txt``

When the following AWS CLI command is called, the AWS CLI will submit
requests to download ``a.txt`` and ``A.txt``. Since only
one can exist on a case-insensitive filesystem, the last download to finish
will be the file that's locally available.

.. code-block::

    aws s3 sync s3://examplebucket ./mylocaldir

Detecting and handling case conflicts
=====================================
To detect and handle case conflicts, you can specify the ``--case-conflict``
parameter. The following values are valid options:

* ``error`` - When a case conflict is detected, the command will immediately
  fail and abort in-progress downloads.
* ``warn`` - When a case conflict is detected, the AWS CLI will
  display a warning.
* ``skip`` - When a case conflict is detected, the command will skip
  downloading the object and continue and display a warning.
* ``ignore`` - (Default) Case conflicts will not be detected or handled.


Continuing the prior example, the following describes what happens when
appending the ``--case-conflict`` parameter with possible values:

``--case-conflict error``

1. Submit a download request for ``A.txt``.
2. Detect that ``a.txt`` conflicts with an object that's been submitted for download.
3. Throw an error. If ``A.txt`` finished downloading, it will be locally available. Otherwise, the download request for ``A.txt`` will be aborted.

``--case-conflict warn``

1. Submit a download request for ``A.txt``.
2. Detect that ``a.txt`` conflicts with an object that's been submitted for download.
3. Display a warning.
4. Submit a download request for ``a.txt``, downloading ``A.txt`` and ``a.txt`` in parallel.

``--case-conflict skip``

1. Submit a download request for ``A.txt``.
2. Detect that ``a.txt`` conflicts with an object that's been submitted for download.
3. Skip downloading ``a.txt`` and continue.

``--case-conflict ignore``

1. Submit a download request for ``A.txt``.
2. Submit a download request for ``a.txt``, downloading ``A.txt`` and ``a.txt`` in parallel.

If your local filesystem is case-sensitive, there's no need to detect and
handle case conflicts. We recommend setting ``--case-conflict ignore``
in this case.

S3 Express directory buckets
============================
Detecting case conflicts is **NOT** supported when the source is an S3 Express
directory bucket. When operating on directory buckets, valid values for the
``--case-conflict`` parameter are:

* ``warn``
* ``ignore``

The following values are invalid when operating on directory buckets:

* ``error``
* ``skip``

For example, calling the following command will fail:

.. code-block::

    aws s3 cp s3://mydirbucket--usw2-az1--x-s3 ./mylocaldir --recursive --case-conflict error