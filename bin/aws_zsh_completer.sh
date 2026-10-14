# Source this file to activate auto-completion for Zsh using the bash compatibility helper.
# Usage: source /path/to/zsh_complete.sh
# Typically sourced in .zshrc. Ensure `compinit` is run before sourcing this script.
#
# Note:
# - The _bash_complete function exports COMP_LINE and COMP_POINT to maintain compatibility with older Zsh versions.
# - Zsh versions after commit edab1d3dbe61da7efe5f1ac0e40444b2ec9b9570 do not require this workaround.
#
# Prerequisites:
# - Ensure bashcompinit is installed and functional.

autoload -Uz bashcompinit
bashcompinit -i || { echo "Error: bashcompinit failed to initialize."; return 1; }

# Main function for bash-style completion in Zsh
_bash_complete() {
  local ret=1
  local -a suf matches
  local -x COMP_POINT COMP_CWORD
  local -a COMP_WORDS COMPREPLY BASH_VERSINFO
  local -x COMP_LINE="$words"
  local -A savejobstates savejobtexts

  # Compatibility adjustments for Zsh environment
  (( COMP_POINT = 1 + ${#${(j. .)words[1,CURRENT]}} + $#QIPREFIX + $#IPREFIX + $#PREFIX ))
  (( COMP_CWORD = CURRENT - 1 ))
  COMP_WORDS=( $words )
  BASH_VERSINFO=( 2 05b 0 1 release )

  # Save current job states
  savejobstates=( ${(kv)jobstates} )
  savejobtexts=( ${(kv)jobtexts} )

  # Handle 'nospace' suffix
  [[ ${argv[${argv[(I)nospace]:-0}-1]} = -o ]] && suf=( -S '' )

  # Generate matches using bash-style completion
  matches=( ${(f)"$(compgen $@ -- ${words[CURRENT]})"} )

  # Add matches to completion system
  if [[ -n $matches ]]; then
    if [[ ${argv[${argv[(I)filenames]:-0}-1]} = -o ]]; then
      compset -P '*/' && matches=( ${matches##*/} )
      compset -S '/*' && matches=( ${matches%%/*} )
      compadd -Q -f "${suf[@]}" -a matches && ret=0
    else
      compadd -Q "${suf[@]}" -a matches && ret=0
    fi
  fi

  # Default fallback if no matches found
  if (( ret )); then
    if [[ ${argv[${argv[(I)default]:-0}-1]} = -o ]]; then
      _default "${suf[@]}" && ret=0
    elif [[ ${argv[${argv[(I)dirnames]:-0}-1]} = -o ]]; then
      _directories "${suf[@]}" && ret=0
    fi
  fi

  return ret
}

# Register AWS completer
complete -C aws_completer aws

# Optional: Uncomment for debugging
echo "Auto-completion setup for Zsh complete."
