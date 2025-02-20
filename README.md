This is my blog, powered by [quarto](https://quarto.org). 
For more details about site content see [the deployed instance](acederberg.io).
To see coverage reports, got see [the artifacts on github pages](https://acederberg.github.io/quarto-maths/).


# Running

For all set ups, make the configuration dir ``config`` and provide the kaggle
configuration in ``config/kaggle/kaggle.json``:

```bash
mkdir config/kaggle -p
```


## With Docker Compose

To run in development mode, use docker compose like

```bash
docker compose --file docker/compose.yaml
```


This will provide access to ``quarto``, ``python``, and ``r``.


## The Hard Way

First, ensure that ``quarto>=1.6`` is installed. Then set up a virtual 
environment using `pyenv` and add install the dependencies using ``poetry``:

```bash
# Add python 3.11
pyenv install 3.11

# Create a virual environment
pyenv virtualenv 3.11 blog

# Make sure that the executables are seen
export PATH=$PATH:$VIRTUAL_ENV/bin

# Verify python version. Should be under ``~/.pyenv``
which python
which pip

# Install poetry
pip install poetry

# Install with poetry
poetry install

# Run the development server
acederbergio serve dev
```


# Editing

In theory this should work but I am yet to do this myself. So be aware this is 
only roughly the process of setting up neovim to play nice with the project
and virtual environment.

```bash
# Create an ipython kernel. This is necessary to use `molten.nvim` inside of
# neovim. It neads `pynvim` to be setup correctly.
poetry run pip install pynvim
poetry run python -m ipykernal install --user --name blog

git clone https://github.com/acederberg/nvim-ez --output=~/.config/nvim
```

Next, open `neovim` and run `:Lazy` in normal and then install the dependencies 
by hitting `I`.


# Building

To render the website, just 

```bash
cd blog
quarto add quarto-ext/iclude-code-files
quarto render
cd -
```


To build the docker image, run 


```bash
export ACEDERBERG_IO_GOOGLE_TRACKING_ID="tracking id here"
docker build --tag acederberg/quarto-blog-builder \
    --file ./docker/dockerfile \
    --secret id=kaggle_json,src=./config/kaggle/kaggle.json . \
    --secret id=google_tracking_id,env=ACEDERBERG_IO_GOOGLE_TRACKING_ID
```


or use the production compose project:


```bash
export ACEDERBERG_IO_GOOGLE_TRACKING_ID="tracking id here"
docker compose --file docker/compose.prod.yaml build
```


To verify the build metatags use ``scripts.meta``.
