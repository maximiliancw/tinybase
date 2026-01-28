# Deployment Guide

This guide covers deploying TinyBase to production environments.

## Deployment Options

<div class="grid cards" markdown>

- :material-docker: [**Docker**](docker.md)

  Deploy TinyBase using containers. Ideal for cloud platforms and orchestration.

- :material-server: [**Production**](production.md)

  Best practices for production deployments, security, and performance.

- :material-shield-lock: [**Security**](security.md)

  Security considerations, best practices, and hardening guide for production.

</div>

## Quick Deploy

### Docker (Recommended)

```bash
docker build -t tinybase .
docker run -p 8000:8000 -v $(pwd)/data:/data tinybase
```

### Manual

```bash
pip install tinybase
tinybase init --admin-email admin@example.com --admin-password secure123
tinybase serve --host 0.0.0.0 --port 8000
```

## Deployment Checklist

Before deploying to production:

- [ ] **Security**

  - [ ] Set strong admin password
  - [ ] Configure HTTPS (via reverse proxy)
  - [ ] Set appropriate CORS origins
  - [ ] Review token TTL settings

- [ ] **Configuration**

  - [ ] Set `debug = false`
  - [ ] Set appropriate `log_level`
  - [ ] Configure database path
  - [ ] Review scheduler settings

- [ ] **Infrastructure**

  - [ ] Set up reverse proxy (nginx/caddy)
  - [ ] Configure SSL/TLS certificates
  - [ ] Set up monitoring
  - [ ] Configure backups

- [ ] **Testing**

  - [ ] Test all API endpoints
  - [ ] Verify authentication flow
  - [ ] Test scheduled functions
  - [ ] Load test if needed

## Architecture Patterns

### Single Server

```
┌─────────────────────────────────────┐
│            Your Server              │
│  ┌───────────┐    ┌──────────────┐  │
│  │  Caddy/   │───▶│   TinyBase   │  │
│  │  Nginx    │    │  (Uvicorn)   │  │
│  └───────────┘    └──────────────┘  │
│        │                  │         │
│        ▼                  ▼         │
│   SSL/HTTPS         SQLite DB       │
└─────────────────────────────────────┘
```

Simple setup for small to medium applications:

- Reverse proxy handles TLS
- TinyBase runs directly
- SQLite for storage

### Docker Compose

```
┌─────────────────────────────────────┐
│         Docker Compose              │
│  ┌───────────┐    ┌──────────────┐  │
│  │  Traefik  │───▶│   TinyBase   │  │
│  │           │    │  Container   │  │
│  └───────────┘    └──────────────┘  │
│        │                  │         │
│        ▼                  ▼         │
│   Let's Encrypt    Volume: /data    │
└─────────────────────────────────────┘
```

Containerized deployment with:

- Automatic SSL via Traefik
- Persistent data volume
- Easy scaling

### Cloud Platform

```
┌─────────────────────────────────────┐
│         Cloud Platform              │
│  ┌───────────┐    ┌──────────────┐  │
│  │   Load    │───▶│   TinyBase   │  │
│  │  Balancer │    │    Pod(s)    │  │
│  └───────────┘    └──────────────┘  │
│        │                  │         │
│        ▼                  ▼         │
│   Managed SSL      Shared Storage   │
└─────────────────────────────────────┘
```

For cloud platforms:

- Managed load balancer
- Persistent volume claim
- Container orchestration

## Environment Variables

Essential environment variables for production:

```bash
# Server
TINYBASE_SERVER_HOST=0.0.0.0
TINYBASE_SERVER_PORT=8000
TINYBASE_DEBUG=false
TINYBASE_LOG_LEVEL=warning

# Database
TINYBASE_DB_URL=sqlite:////data/tinybase.db

# Auth
TINYBASE_AUTH_TOKEN_TTL_HOURS=8

# CORS (set specific origins)
TINYBASE_CORS_ALLOW_ORIGINS=https://myapp.com

# Scheduler
TINYBASE_SCHEDULER_ENABLED=true
```

## Data Persistence

### SQLite Considerations

TinyBase uses SQLite by default. For production:

1. **Store database on persistent storage**

   ```bash
   TINYBASE_DB_URL=sqlite:////var/lib/tinybase/tinybase.db
   ```

1. **Regular backups**

   ```bash
   # Simple backup
   cp /var/lib/tinybase/tinybase.db /backups/tinybase-$(date +%Y%m%d).db

   # SQLite online backup
   sqlite3 /var/lib/tinybase/tinybase.db ".backup /backups/tinybase.db"
   ```

1. **Monitor database size**

   - SQLite handles databases up to several GB efficiently
   - For larger needs, consider implementing archival

### Docker Volumes

```yaml
volumes:
  tinybase-data:
    driver: local

services:
  tinybase:
    volumes:
      - tinybase-data:/data
```

## Monitoring

### Health Check

TinyBase serves at `/docs` which can be used for health checks:

```bash
curl -f http://localhost:8000/docs || exit 1
```

### Logging

Configure logging level:

```toml
[server]
log_level = "info"  # debug, info, warning, error
```

View logs:

```bash
# Docker
docker logs -f tinybase

# Systemd
journalctl -u tinybase -f
```

### Metrics

Monitor these metrics:

- Request latency (via logs)
- Error rate (function call status)
- Database size
- Memory usage

## Security Hardening

See the [Security Guide](security.md) for comprehensive security recommendations:

- HTTPS/TLS configuration
- Authentication & token management
- Resource limits and DoS protection
- Rate limiting
- Function security
- Database security
- Monitoring and audit logging

## Next Steps

- [Docker Deployment](docker.md) - Container-based deployment
- [Production Guide](production.md) - Performance and optimization
- [Security Guide](security.md) - Security best practices
- [Configuration](../getting-started/configuration.md) - All configuration options
