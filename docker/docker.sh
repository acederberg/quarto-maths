# NOTE: Get python dependencies.

if [[ ! $ACEDERBERG_IO_VENV ]]; then export ACEDERBERG_IO_VENV="/home/docker/.venv"; fi
if [[ ! $ACEDERBERG_IO_WORKDIR ]]; then export ACEDERBERG_IO_WORKDIR="/home/docker"; fi
export PATH="$PATH:/home/docker/.local/bin"

mkdir --parents $ACEDERBERG_IO_VENV

if [[ $(ls $ACEDERBERG_IO_VENV | wc --lines) -eq 0 ]]; then
  echo "Virtual environment does not exist. Creating under \`$ACEDERBERG_IO_VENV\`."
  python3.10 -m venv $ACEDERBERG_IO_VENV
else
  echo "Virtual environment already exists."
fi

source $ACEDERBERG_IO_VENV/bin/activate

python3.10 -m pip install poetry >>/dev/null

cd $ACEDERBERG_IO_WORKDIR/app
poetry install --no-root >>/dev/null
