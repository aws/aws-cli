Overview
========

This document describes how to test and lint the ``install`` script used
to install the AWS CLI exe bundle.

Running the tests
-----------------

The test suite utilizes `Bats <https://github.com/sstephenson/bats>`_ to run
the tests. To run the tests, first make sure you first install Bats::

     $ brew install bats


And then run Bats from within this ``tests`` directory::

     $ bats .


Linting
-------
To help catch potential issues in the shell script and tests, you should also
lint the scripts. To lint the shell scripts, use
`ShellCheck <https://github.com/koalaman/shellcheck>`_. It can be installed
with ``brew``::

     $ brew install shellcheck


Then can be ran on both the ``install`` shell script and the ``install.bats``
test file::

   $ shellcheck ../assets/install
   $ shellcheck install.bats

