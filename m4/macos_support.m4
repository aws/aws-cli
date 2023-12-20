AC_DEFUN([AC_CHECK_PENDING_MACOS_END_OF_SUPPORT], [
    min_version='$1'
    end_support_date='$2'

    AC_MSG_CHECKING([for macOS version support])
    ac_macos_version=`(sw_vers -productVersion) 2>/dev/null || echo unknown`

    if test "$ac_macos_version" = unknown; then
        AC_MSG_RESULT([unknown])
    else
        sys_version_major=`echo "$ac_macos_version" | \
            sed 's/\([[0-9]]*\)\.\([[0-9]]*\).*/\1/'`
        sys_version_minor=`echo "$ac_macos_version" | \
            sed 's/\([[0-9]]*\)\.\([[0-9]]*\).*/\2/'`

        min_version_major=`echo "$min_version" | \
            sed 's/\([[0-9]]*\)\.\([[0-9]]*\).*/\1/'`
        min_version_minor=`echo "$min_version" | \
            sed 's/\([[0-9]]*\)\.\([[0-9]]*\).*/\2/'`

        if test "$sys_version_major" -lt "$min_version_major" || \
            test "$sys_version_major" -eq "$min_version_major" -a \
            "$sys_version_minor" -lt "$min_version_minor"; then
            AC_MSG_RESULT([pending-end-of-support])
            AC_MSG_WARN(m4_normalize([
                On $end_support_date, the AWS CLI v2 will drop support
                for macOS versions below $min_version. macOS $ac_macos_version
                was detected for this system. Please upgrade to macOS version
                $min_version or later to ensure compatibility with future versions
                of AWS CLI v2. For more information, please visit:
                https://aws.amazon.com/blogs/developer/macos-support-policy-updates-for-the-aws-cli-v2/
            ]))
        else
            AC_MSG_RESULT([supported])
        fi
    fi
])
