FROM python:3.11 AS builder
RUN python -m pip install pipx
ENV PATH="/root/.local/bin:{$PATH}"
RUN pipx install poetry
RUN pipx inject poetry poetry-plugin-bundle
WORKDIR /src
COPY . .
RUN poetry bundle venv --python=/usr/local/bin/python /venv

FROM python:3.11
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:${PATH}"
CMD [ "/venv/bin/chatbot" ]