# Docker Deployment

Deploy TinyBase using Docker for consistent, reproducible deployments.

## Quick Start

### Using Pre-built Image

```bash
# Pull and run (when published to Docker Hub)
docker run -p 8000:8000 -v tinybase-data:/data maximiliancw/tinybase
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/maximiliancw/tinybase.git
cd tinybase

# Build image
docker build -t tinybase .

# Run container
docker run -p 8000:8000 -v $(pwd)/data:/data tinybase
```

## Dockerfile

TinyBase includes a multi-stage Dockerfile:

```dockerfile title="Dockerfile"
# Stage 1: Build Admin UI
FROM node:20-slim AS ui-builder
WORKDIR /app
COPY app/package.json app/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY app/ ./
RUN yarn build

# Stage 2: Python Runtime
FROM python:3.11-slim
WORKDIR /app

# Install uv
RUN pip install uv

# Copy and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application
COPY tinybase/ ./tinybase/
COPY --from=ui-builder /app/dist ./tinybase/static/app/

# Create data directory
RUN mkdir -p /data

# Environment
ENV TINYBASE_DB_URL=sqlite:////data/tinybase.db
ENV TINYBASE_ADMIN_STATIC_DIR=builtin

EXPOSE 8000
CMD ["uv", "run", "tinybase", "serve", "--host", "0.0.0.0"]
```

## Docker Compose

### Basic Setup

```yaml title="docker-compose.yml"
version: '3.8'

services:
  tinybase:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - tinybase-data:/data
      - ./functions:/app/functions:ro
    environment:
      - TINYBASE_ADMIN_EMAIL=admin@example.com
      - TINYBASE_ADMIN_PASSWORD=changeme
      - TINYBASE_LOG_LEVEL=info
    restart: unless-stopped

volumes:
  tinybase-data:
```

### With Reverse Proxy (Traefik)

```yaml title="docker-compose.yml"
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
    restart: unless-stopped

  tinybase:
    build: .
    volumes:
      - tinybase-data:/data
      - ./functions:/app/functions:ro
    environment:
      - TINYBASE_ADMIN_EMAIL=admin@example.com
      - TINYBASE_ADMIN_PASSWORD=${TINYBASE_ADMIN_PASSWORD}
      - TINYBASE_CORS_ALLOW_ORIGINS=https://api.example.com
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tinybase.rule=Host(`api.example.com`)"
      - "traefik.http.routers.tinybase.entrypoints=websecure"
      - "traefik.http.routers.tinybase.tls.certresolver=letsencrypt"
      - "traefik.http.services.tinybase.loadbalancer.server.port=8000"
    restart: unless-stopped

volumes:
  tinybase-data:
  letsencrypt:
```

### With Caddy

```yaml title="docker-compose.yml"
version: '3.8'

services:
  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    restart: unless-stopped

  tinybase:
    build: .
    volumes:
      - tinybase-data:/data
      - ./functions:/app/functions:ro
    environment:
      - TINYBASE_ADMIN_EMAIL=admin@example.com
      - TINYBASE_ADMIN_PASSWORD=${TINYBASE_ADMIN_PASSWORD}
    restart: unless-stopped

volumes:
  tinybase-data:
  caddy-data:
  caddy-config:
```

```text title="Caddyfile"
api.example.com {
    reverse_proxy tinybase:8000
}
```

## Environment Variables

Pass configuration via environment variables:

```yaml
environment:
  # Server
  - TINYBASE_SERVER_HOST=0.0.0.0
  - TINYBASE_SERVER_PORT=8000
  - TINYBASE_DEBUG=false
  - TINYBASE_LOG_LEVEL=info
  
  # Database
  - TINYBASE_DB_URL=sqlite:////data/tinybase.db
  
  # Auth
  - TINYBASE_AUTH_TOKEN_TTL_HOURS=24
  - TINYBASE_ADMIN_EMAIL=admin@example.com
  - TINYBASE_ADMIN_PASSWORD=${ADMIN_PASSWORD}
  
  # CORS
  - TINYBASE_CORS_ALLOW_ORIGINS=https://myapp.com
  
  # Scheduler
  - TINYBASE_SCHEDULER_ENABLED=true
```

## Volume Mounts

### Data Volume

Persist database and files:

```yaml
volumes:
  - tinybase-data:/data
```

### Custom Functions

Mount your functions directory:

```yaml
volumes:
  - ./functions:/app/functions:ro
```

### Custom Configuration

Mount configuration file:

```yaml
volumes:
  - ./tinybase.toml:/app/tinybase.toml:ro
```

## Health Checks

Add Docker health checks:

```yaml
services:
  tinybase:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Logging

### Docker Logging

```yaml
services:
  tinybase:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### View Logs

```bash
# Follow logs
docker-compose logs -f tinybase

# Last 100 lines
docker-compose logs --tail=100 tinybase
```

## Backup and Restore

### Backup

```bash
# Stop container (for consistency)
docker-compose stop tinybase

# Backup volume
docker run --rm \
  -v tinybase-data:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/tinybase-$(date +%Y%m%d).tar.gz -C /data .

# Restart container
docker-compose start tinybase
```

### Online Backup (SQLite)

```bash
docker-compose exec tinybase \
  sqlite3 /data/tinybase.db ".backup /data/backup.db"
```

### Restore

```bash
# Stop container
docker-compose stop tinybase

# Restore volume
docker run --rm \
  -v tinybase-data:/data \
  -v $(pwd)/backups:/backup:ro \
  alpine tar xzf /backup/tinybase-20240101.tar.gz -C /data

# Start container
docker-compose start tinybase
```

## Scaling Considerations

### Single Container (Default)

TinyBase with SQLite works best as a single container:

- SQLite doesn't support multiple writers
- Scheduler should run on only one instance
- Suitable for most use cases

### Multiple Containers (Advanced)

For read scaling, you can:

1. Run one primary with scheduler
2. Run read replicas without scheduler

```yaml
services:
  tinybase-primary:
    environment:
      - TINYBASE_SCHEDULER_ENABLED=true
    volumes:
      - tinybase-data:/data

  tinybase-replica:
    environment:
      - TINYBASE_SCHEDULER_ENABLED=false
    volumes:
      - tinybase-data:/data:ro  # Read-only
```

!!! warning "SQLite Limitations"
    SQLite with multiple writers can cause issues. For high-write workloads, consider architectural changes.

## Security

### Non-root User

The default Dockerfile runs as root. For production:

```dockerfile
# Add non-root user
RUN useradd -m -u 1000 tinybase
RUN chown -R tinybase:tinybase /app /data
USER tinybase
```

### Read-only Root Filesystem

```yaml
services:
  tinybase:
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - tinybase-data:/data
```

### Network Isolation

```yaml
services:
  tinybase:
    networks:
      - internal
      - proxy
    
  traefik:
    networks:
      - proxy

networks:
  internal:
    internal: true
  proxy:
    external: true
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs tinybase

# Check container status
docker-compose ps

# Run interactively
docker-compose run --rm tinybase bash
```

### Database Issues

```bash
# Check database
docker-compose exec tinybase sqlite3 /data/tinybase.db ".tables"

# Reset database
docker-compose down -v
docker-compose up -d
```

### Permission Issues

```bash
# Check volume permissions
docker-compose exec tinybase ls -la /data

# Fix permissions
docker-compose exec tinybase chown -R 1000:1000 /data
```

## Cloud Deployments

### AWS ECS

```json
{
  "containerDefinitions": [
    {
      "name": "tinybase",
      "image": "your-ecr-repo/tinybase:latest",
      "portMappings": [
        {"containerPort": 8000, "hostPort": 8000}
      ],
      "environment": [
        {"name": "TINYBASE_DB_URL", "value": "sqlite:////data/tinybase.db"}
      ],
      "mountPoints": [
        {"sourceVolume": "tinybase-data", "containerPath": "/data"}
      ]
    }
  ],
  "volumes": [
    {"name": "tinybase-data", "efsVolumeConfiguration": {...}}
  ]
}
```

### Google Cloud Run

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: tinybase
spec:
  template:
    spec:
      containers:
        - image: gcr.io/your-project/tinybase
          ports:
            - containerPort: 8000
          env:
            - name: TINYBASE_DB_URL
              value: sqlite:////data/tinybase.db
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: tinybase-pvc
```

## See Also

- [Production Guide](production.md) - Security and performance
- [Configuration](../getting-started/configuration.md) - All options
- [Deployment Overview](index.md) - Architecture patterns

