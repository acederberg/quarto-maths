This is my blog, powered by [quarto](https://quarto.org). 
For more details about site content see [the deployed instance](acederberg.io).
To see coverage reports, got see [the artifacts on github pages](https://acederberg.github.io/quarto-maths/).


# Running

For all set ups, make the configuration dir ``config`` and provide your kaggle 
configuration in ``config/kaggle/kaggle.json``. 


## With Docker Compose

To run in development mode, use docker compose like

```bash
docker compose --file docker/compose.yaml
```


This will provide access to ``quarto``, ``python``, and ``r``.


## The Hard Way

First, ensure that ``quarto`` is installed. Then setup a virtual environment and 
add install the dependencies using ``poetry``:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install poetry
poetry install
```


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
