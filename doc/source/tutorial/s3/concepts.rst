This section explains concepts and notations that are prominent in the set
of commands provided.

Path Argument Type
++++++++++++++++++
Whenever using a command, at least one path argument must be specified.  There
are two types of path arguments: ``LocalPath`` and ``S3Path``.

``LocalPath``: represents the path of a local file or directory.  It can be
written as an absolute path or relative path.

``S3Path``: represents the location of a S3 object, prefix, or bucket.  This
must be written in the form ``s3://mybucket/mykey`` where ``mybucket`` is
the specified S3 bucket, ``mykey`` is the specified S3 key.  The path argument
must begin with ``s3://`` in order to denote that the path argument refers to
a S3 object. Note that prefixes are separated by forward slashes. For
example, if the S3 object ``myobject`` had the prefix ``myprefix``, the
S3 key would be ``myprefix/myobject``, and if the object was in the bucket
``mybucket``, the ``S3Path`` would be ``s3://mybucket/myprefix/myobject``.

Order of Path Arguments
+++++++++++++++++++++++
Every command takes one or two positional path arguments.  The first path
argument represents the source, which is the local file/directory or S3
object/prefix/bucket that is being referenced.  If there is a second path
argument, it represents the destination, which is is the local file/directory
or S3 object/prefix/bucket that is being operated on.  Commands with only
one path argument do not have a destination because the operation is being
performed only on the source.

Single Local File and S3 Object Operations
++++++++++++++++++++++++++++++++++++++++++
Some commands perform operations only on single files and S3 objects.  The
following commands are single file/object operations if no ``--recursive``
flag is provided.

    * ``get``
    * ``mv``
    * ``rm``
    * ``put``
    * ``copy``  

For this type of operation, the first path argument, the source, must exist
and be a local file or S3 object.  The second path argument, the destination,
can be the name of a local file, local directory, S3 object, S3 prefix,
or S3 bucket.

The destination is indicated as a local directory, S3 prefix, or S3 bucket
if it ends with a forward slash or back slash.  The use of slash depends
on the path argument type.  If the path argument is a ``LocalPath``,
the type of slash is the separator used by the operating system.  If the
path is a ``S3Path``, the forward slash must always be used.  If a slash
is at the end of the destination, the destination file or object will
adopt the name of the source file or object.  Otherwise, if there is no
slash at the end, the file or object will be saved under the name provided.
See examples in ``get``, ``mv``, ``put``, ``copy`` to illustrate this
description.

Directory and S3 Prefix Operations
++++++++++++++++++++++++++++++++++
Some commands only perform operations on the contents of a local directory
or S3 prefix/bucket.  Adding or omitting a forward slash or back slash to
the end of any path argument, depending on its type, does not affect the
results of the operation.  The following features will always result in
a directory or S3 prefix/bucket operation.

    * commands: ``sync``, ``mb``, ``rb``, ``ls``
    * parameters: ``--recursive``

Use of Exclude and Include Filters
++++++++++++++++++++++++++++++++++
Currently, there is no support for the use of UNIX style wildcards in
a command's path arguments.  However, most commands have ``--exclude <value>``
and ``--include <value>`` parameters that can achieve the desired result.
These parameters perform pattern matching to either exclude or include
a particular file or object.  The following pattern symbols are supported.

    * ``*``: Matches everything
    * ``?``: Matches any single character
    * ``[sequence]``: Matches any character in ``sequence``
    * ``[!sequence]``: Matches any charater not in ``sequence``

The real power of these parameters is that any number of these parameters
can be passed to a command.  When there are multiple filters, the rule is
the filters that appear later in the command take precedence over filters
that appear earlier in the command.  For example, if the filter parameters
passed to the command were
::

    --exclude * --include *.txt

All files will be excluded from the command except for files ending with 
``.txt``  However, if the order of the filter parameters was changed to
::

    --include *.txt --exclude *

All files will be excluded from the command.       
