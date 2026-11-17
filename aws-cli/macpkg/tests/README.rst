Overview
========

This document describes how to test and lint the macpkg generation scripts and
PKG.

Running the tests
-----------------

The test suite utilizes `Bats <https://github.com/sstephenson/bats>`_ to run
the tests. To run the tests, first make sure you first install Bats::

     $ brew install bats


And then run Bats from within this ``tests`` directory::

     $ bats .

You can point the tests to a custom installer package location by using the
environment variable INSTALLER_TO_TEST. For example to test an installer in your
home directory::

  $ INSTALLER_TO_TEST=~/AWS-CLI-Installer.pkg bats .


Linting
-------
To help catch potential issues in the shell script and tests, you should also
lint the scripts. To lint the shell scripts, use
`ShellCheck <https://github.com/koalaman/shellcheck>`_. It can be installed
with ``brew``::

     $ brew install shellcheck


Then run on the ``scripts/postinstall`` and ``tests/install.bats``
test files::

   $ shellcheck scripts/postinstall tests/install.bats
