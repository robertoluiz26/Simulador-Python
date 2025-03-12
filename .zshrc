export PATH="$HOME/.local/bin:$PATH"
alias ll="ls -alh"

# Configuração do pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Inicialização do pyenv
if command -v pyenv 1>/dev/null 2>&1; then
  eval "$(pyenv init --path)"
  eval "$(pyenv init -)"
fi

# (Opcional) Se você usa pyenv-virtualenv para ambientes virtuais:
if command -v pyenv-virtualenv 1>/dev/null 2>&1; then
  eval "$(pyenv virtualenv-init -)"
fi
alias python="python3"

# Configuração do Gurobi
export GUROBI_HOME="/home/robertoluiz/gurobi/gurobi1201/linux64"
export PATH="${GUROBI_HOME}/bin:${PATH}"
export LD_LIBRARY_PATH="${GUROBI_HOME}/lib:${LD_LIBRARY_PATH}"
export GRB_LICENSE_FILE="/home/robertoluiz/gurobi/gurobi.lic"
