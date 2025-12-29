FROM python:3.11.9 AS alembic

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt update && apt upgrade -y && \
    apt install -y nano unixodbc unixodbc-dev build-essential curl

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .

RUN bash -c "source $HOME/.cargo/env && pip install --no-cache-dir maturin"
RUN bash -c "source $HOME/.cargo/env && pip install --no-cache-dir --no-build-isolation -r requirements.txt"

COPY . .

RUN chmod +x /app/entrypoint.sh
RUN mkdir -p data/{raw,processed,results,models,indexes,objects}

EXPOSE 7777