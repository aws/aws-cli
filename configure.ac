AC_CONFIG_MACRO_DIRS([m4])
AC_INIT([awscli], [2.7.31])
AC_CONFIG_SRCDIR([bin/aws])
AM_PATH_PYTHON([3.8])

AC_MSG_CHECKING(for --with-install-type)
AC_ARG_WITH(install_type,
            AS_HELP_STRING([--with-install-type=@<:@system-sandbox|portable-exe@:>@],
                           [Specify type of AWS CLI installation. Options are:
                            "portable-exe", "system-sandbox" (default is "system-sandbox")]),
[],
[with_install_type=system-sandbox])
AS_CASE($with_install_type,
    [portable-exe],[INSTALL_TYPE=portable-exe],
    [system-sandbox],[INSTALL_TYPE=system-sandbox],
    [AC_MSG_ERROR([--with-install-type=portable-exe|system-sandbox])])
AC_SUBST(INSTALL_TYPE)
AC_MSG_RESULT($with_install_type)

AC_MSG_CHECKING(for --with-download-deps)
AC_ARG_WITH(download_deps,
            AS_HELP_STRING([--with-download-deps],
                           [Download all dependencies and use those when
                            building the AWS CLI. If not specified, the dependencies
                            (including all python packages) must be installed
                            on your system]),
[],
[with_download_deps=no]
)
if test "$with_download_deps" = no; then
     ${PYTHON} ${srcdir}/backends/build_system validate-env --artifact $with_install_type || AC_MSG_ERROR("Python dependencies not met")
     DOWNLOAD_DEPS_FLAG=""
else
     DOWNLOAD_DEPS_FLAG=--download-deps
fi
AC_MSG_RESULT($with_download_deps)
AC_SUBST(DOWNLOAD_DEPS_FLAG)

AC_CONFIG_FILES([Makefile])
AC_OUTPUT
OVERRIDE_HELP
