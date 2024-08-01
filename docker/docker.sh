# NOTE: Get python dependencies.

if [[ ! $ACEDERBERG_IO_VENV ]]; then export ACEDERBERG_IO_VENV="/home/docker/.venv"; fi
if [[ ! $ACEDERBERG_IO_WORKDIR ]]; then export ACEDERBERG_IO_WORKDIR="/home/docker/app"; fi
if [[ ! $ACEDERBERG_IO_BUILD_LOG ]]; then export ACEDERBERG_IO_BUILD_LOG="/dev/null"; fi

export PATH="$PATH:/home/docker/.local/bin"

mkdir --parents $ACEDERBERG_IO_VENV

if [[ $(ls $ACEDERBERG_IO_VENV | wc --lines) -eq 0 ]]; then
  echo "Virtual environment does not exist. Creating under \`$ACEDERBERG_IO_VENV\`."
  python3.10 -m venv $ACEDERBERG_IO_VENV
else
  echo "Virtual environment already exists."
fi

source $ACEDERBERG_IO_VENV/bin/activate

python3.10 -m pip install poetry >>$ACEDERBERG_IO_BUILD_LOG

cd $ACEDERBERG_IO_WORKDIR
poetry install --no-root >>$ACEDERBERG_IO_BUILD_LOG

which python3.10
