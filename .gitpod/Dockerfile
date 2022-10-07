FROM gitpod/workspace-full

USER gitpod

COPY --chown=gitpod ./requirements.txt /requirements.txt
RUN pip install --upgrade pip \
    pip install -r /requirements.txt \
    pre-commit install
