# NOTE: Borrowed from https://github.com/analythium/quarto-docker-examples/blob/main/Dockerfile.base
#       This is not optimal for CI, the image is huge and will be slow af in actions/pipelines.
FROM eddelbuettel/r2u:20.04 AS quarto

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    pandoc-citeproc \
    curl \
    gdebi-core \
    && rm -rf /var/lib/apt/lists/*

RUN install.r \
    shiny \
    jsonlite \
    ggplot2 \
    htmltools \
    remotes \
    renv \
    knitr \
    rmarkdown \
    quarto

# ARG QUARTO_VERSION="0.9.522"
# RUN curl -o quarto-linux-amd64.deb -L https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb
RUN curl -LO https://quarto.org/download/latest/quarto-linux-amd64.deb
RUN gdebi --non-interactive quarto-linux-amd64.deb

CMD ["bash"]


# --------------------------------------------------------------------------- #
FROM quarto AS builder

COPY . /quarto
RUN quarto render /quarto

CMD ["bash"]


# --------------------------------------------------------------------------- #
# https://hub.docker.com/_/node/tags

FROM node:lts-alpine3.20 AS production

# RUN npm install http-server
USER node

WORKDIR /app
COPY --from=builder /quarto/build /app
RUN npm install http-server


