==========================
Building The Documentation
==========================

Before building the documentation, make sure you have Python 3.6,
the awscli, and all the necessary dependencies installed.  You can
install dependencies by using the requirements-docs.txt file at the
root of this repo::

    pip install -r requirements-docs.txt

The process for building the documentation is:

* Run ``make html`` which will build all of the HTML documentation
  into the ``build/html`` directory.

* Run ``make man`` which will build all of the man pages into
  ``../doc/man/man1``.  These files are included in the source
  distribution and installed by ``python setup.py install``.

* Run ``make text`` which will build all of the text pages that
  are used for interactive help on the Windows platform.  These files
  are included in the source distribution and installed by
  ``python setup.py install``.

You can perform all of these tasks by running ``make all`` in this
directory.  If you have previously built the documentation and want
to regenerate it, run ``make clean`` first.
