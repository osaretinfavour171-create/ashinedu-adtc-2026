FROM ubuntu:22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    curl wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Go for building DocReader
RUN wget -q https://go.dev/dl/go1.22.4.linux-amd64.tar.gz -O /tmp/go.tar.gz \
    && tar -C /usr/local -xzf /tmp/go.tar.gz \
    && rm /tmp/go.tar.gz
ENV PATH=$PATH:/usr/local/go/bin
ENV GOPATH=/root/go
ENV PATH=$PATH:$GOPATH/go/bin

WORKDIR /app

# Copy Go source and build DocReader
COPY app/docreader/ /app/app/docreader/
RUN cd /app/app/docreader && go build -o /app/tools/docreader .

# Copy Python app
COPY app/ /app/app/
COPY tests/ /app/tests/
COPY start.sh /app/
COPY download_model.sh /app/

# Copy data files
COPY app/data/ /app/app/data/

# Make scripts executable
RUN chmod +x /app/start.sh /app/download_model.sh

# Expose ports
EXPOSE 8765 8080

# Default: start the system (without model — user must run download_model.sh first)
CMD ["bash", "start.sh"]
