FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .[dev,p2p]

RUN useradd -u 10001 gossipmesh && chown -R gossipmesh:gossipmesh /app
USER gossipmesh

EXPOSE 8080
CMD ["python", "-m", "gossipmesh.main"]
