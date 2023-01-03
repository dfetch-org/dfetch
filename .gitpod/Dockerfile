FROM gitpod/workspace-full:latest

USER gitpod

COPY --chown=gitpod ./pyproject.toml /pyproject.toml
RUN pip install --upgrade pip && \
    pip install .[development] && \
    pre-commit install
