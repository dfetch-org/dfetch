FROM gitpod/workspace-full:latest

USER gitpod

RUN pyenv install 3.11 \
    && pyenv global 3.11

RUN sudo apt-get update \
 && sudo apt-get install -y \
    pv \
    plantuml \
 && sudo rm -rf /var/lib/apt/lists/*

COPY --chown=gitpod . .
RUN pip install --upgrade pip  \
    && pip install -e .[development,docs,test,casts]  \
    && pre-commit install --install-hooks
