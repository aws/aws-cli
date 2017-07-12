#compdef aws

# Source this file to activate auto completion for zsh using the bash
# compatibility helper.
#
# This can be done in either of the following ways:
#
#   - By explicitly by sourcing the script, typically somewhere in your .zshrc
#     like so:
#         % source /path/to/aws_zsh_completer.sh
#
#   - By making it available as '_aws' in your zsh '$fpath' like so:
#         % ls -s /path/to/aws_zsh_completer.sh /usr/local/share/zsh/site-functions
#     (assuming '/usr/local/share/zsh/site-functions' is already in '$fpath').
#
# Make sure to run `compinit` before sourcing this, which is usually a given.
#
# Note, the overwrite of _bash_complete() is to export COMP_LINE and COMP_POINT
# That is only required for zsh <= edab1d3dbe61da7efe5f1ac0e40444b2ec9b9570
# zsh version 5.0.3 onwards has this fully integrated. zsh relases prior to
# that version do not export the required env variables!
#
# See: https://github.com/zsh-users/zsh/commit/edab1d3dbe61da7efe5f1ac0e40444b2ec9b9570
#
# zsh releases prior to that version do not export the required env variables!

# Load and initialize the completion system ignoring insecure directories.
autoload -Uz bashcompinit && bashcompinit -i

# Overwrite _bash_complete() for zsh versions less than 5.0.3 only
autoload -Uz is-at-least
if ! is-at-least 5.0.3; then
  _bash_complete() {
    local ret=1
    local -a suf matches
    local -x COMP_POINT COMP_CWORD
    local -a COMP_WORDS COMPREPLY BASH_VERSINFO
    local -x COMP_LINE="$words"
    local -A savejobstates savejobtexts

    (( COMP_POINT = 1 + ${#${(j. .)words[1,CURRENT]}} + $#QIPREFIX + $#IPREFIX + $#PREFIX ))
    (( COMP_CWORD = CURRENT - 1))
    COMP_WORDS=( $words )
    BASH_VERSINFO=( 2 05b 0 1 release )

    savejobstates=( ${(kv)jobstates} )
    savejobtexts=( ${(kv)jobtexts} )

    [[ ${argv[${argv[(I)nospace]:-0}-1]} = -o ]] && suf=( -S '' )

    matches=( ${(f)"$(compgen $@ -- ${words[CURRENT]})"} )

    if [[ -n $matches ]]; then
      if [[ ${argv[${argv[(I)filenames]:-0}-1]} = -o ]]; then
        compset -P '*/' && matches=( ${matches##*/} )
        compset -S '/*' && matches=( ${matches%%/*} )
        compadd -Q -f "${suf[@]}" -a matches && ret=0
      else
        compadd -Q "${suf[@]}" -a matches && ret=0
      fi
    fi

    if (( ret )); then
      if [[ ${argv[${argv[(I)default]:-0}-1]} = -o ]]; then
        _default "${suf[@]}" && ret=0
      elif [[ ${argv[${argv[(I)dirnames]:-0}-1]} = -o ]]; then
        _directories "${suf[@]}" && ret=0
      fi
    fi

    return ret
  }
fi

complete -C aws_completer aws

# Bind `aws` completion eagerly to `_bash_complete -C aws_completer` and
# suppress stderr to avoid 'can only be called from completion function' warning
_complete aws 2> /dev/null
