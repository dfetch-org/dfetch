FROM gitpod/workspace-full:latest

USER gitpod

COPY --chown=gitpod . .
RUN pip install --upgrade pip  \
    pip install .[development]  \
    pre-commit install
