FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# No CMD, so `docker run -i --rm mtg-mcp` is plain stdio.
# HTTP: docker run --rm -p 8000:8000 mtg-mcp --http --host 0.0.0.0 --port 8000
ENTRYPOINT ["mtg-mcp"]
EXPOSE 8000
# shortcut: nobody cannot write the bundled library. Mount a dir and set MTG_MCP_LIBRARY_DIR to import decks.
USER nobody
