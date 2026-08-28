# Source this file to activate auto completion for zsh using the bash
# compatibility helper.  Make sure to run `compinit` before, which should be
# given usually.
#
# % source /path/to/zsh_complete.sh
#
# Typically that would be called somewhere in your .zshrc.

if (( ! ${+functions[complete]} )); then
  autoload -Uz bashcompinit
  bashcompinit
fi

complete -C aws_completer aws
