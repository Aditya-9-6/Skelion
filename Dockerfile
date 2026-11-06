FROM python:3.12-slim

WORKDIR /app

RUN useradd -u 10001 gossipuser && \
    chown -R gossipuser:gossipuser /app

COPY . /app

USER gossipuser

CMD ["python", "-m", "gossipmesh"]
