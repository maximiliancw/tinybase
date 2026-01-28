# Production Guide

Best practices for deploying TinyBase in production environments.

## Security Checklist

### Essential

- [ ] Use HTTPS (TLS) for all traffic
- [ ] Set strong admin passwords
- [ ] Disable debug mode
- [ ] Configure specific CORS origins
- [ ] Set appropriate token TTL
- [ ] Keep TinyBase updated

### Recommended

- [ ] Use a reverse proxy
- [ ] Enable rate limiting
- [ ] Set up monitoring
- [ ] Configure log aggregation
- [ ] Implement backup strategy
- [ ] Use environment variables for secrets

## HTTPS Configuration

### Using Caddy (Automatic HTTPS)

```text title="Caddyfile"
api.example.com {
    reverse_proxy localhost:8000
}
```

Caddy automatically obtains and renews Let's Encrypt certificates.

### Using Nginx

```nginx title="nginx.conf"
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

## Configuration

### Production Settings

```toml title="tinybase.toml"
[server]
host = "127.0.0.1"      # Bind to localhost (behind proxy)
port = 8000
debug = false           # IMPORTANT: Disable debug
log_level = "warning"   # Reduce log verbosity

[database]
url = "sqlite:////var/lib/tinybase/tinybase.db"

[auth]
token_ttl_hours = 8     # Shorter tokens for security

[cors]
allow_origins = ["https://myapp.com", "https://admin.myapp.com"]

[scheduler]
enabled = true
interval_seconds = 10

[admin]
static_dir = "builtin"
```

### Environment Variables

Use environment variables for sensitive data:

```bash
# .env file (never commit to git)
TINYBASE_ADMIN_EMAIL=admin@example.com
TINYBASE_ADMIN_PASSWORD=very-secure-password-123
```

## Rate Limiting

TinyBase includes built-in rate limiting via SlowAPI:

```python
# Default limits (can be configured)
# - 100 requests per minute for authenticated users
# - 20 requests per minute for public endpoints
```

### Nginx Rate Limiting

Add additional rate limiting at the proxy level:

```nginx
# Define rate limit zone
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

## Database

### SQLite Best Practices

1. **Persistent Storage**

   ```bash
   mkdir -p /var/lib/tinybase
   chown tinybase:tinybase /var/lib/tinybase
   ```

1. **Regular Backups**

   ```bash
   #!/bin/bash
   # backup.sh
   BACKUP_DIR=/var/backups/tinybase
   DB_PATH=/var/lib/tinybase/tinybase.db

   mkdir -p $BACKUP_DIR
   sqlite3 $DB_PATH ".backup $BACKUP_DIR/tinybase-$(date +%Y%m%d-%H%M%S).db"

   # Keep last 7 days
   find $BACKUP_DIR -name "*.db" -mtime +7 -delete
   ```

1. **Schedule Backups**

   ```cron
   0 */6 * * * /opt/tinybase/backup.sh
   ```

### Database Maintenance

Periodic maintenance:

```bash
# Vacuum database (reclaim space)
sqlite3 /var/lib/tinybase/tinybase.db "VACUUM;"

# Analyze for query optimization
sqlite3 /var/lib/tinybase/tinybase.db "ANALYZE;"

# Check integrity
sqlite3 /var/lib/tinybase/tinybase.db "PRAGMA integrity_check;"
```

## Process Management

### Systemd Service

```ini title="/etc/systemd/system/tinybase.service"
[Unit]
Description=TinyBase Server
After=network.target

[Service]
Type=simple
User=tinybase
Group=tinybase
WorkingDirectory=/opt/tinybase
Environment="PATH=/opt/tinybase/.venv/bin"
EnvironmentFile=/opt/tinybase/.env
ExecStart=/opt/tinybase/.venv/bin/tinybase serve
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/tinybase

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable tinybase
sudo systemctl start tinybase
```

### Supervisor

```ini title="/etc/supervisor/conf.d/tinybase.conf"
[program:tinybase]
command=/opt/tinybase/.venv/bin/tinybase serve
directory=/opt/tinybase
user=tinybase
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/tinybase/tinybase.log
```

## Monitoring

### Health Checks

```bash
#!/bin/bash
# healthcheck.sh
curl -sf http://localhost:8000/docs > /dev/null || exit 1
```

### Prometheus Metrics

Export basic metrics via logging:

```python
# In your functions, log metrics
import logging
logger = logging.getLogger(__name__)

@register(name="my_function", ...)
def my_function(ctx, payload):
    start = time.time()
    result = do_work()
    duration = time.time() - start
    logger.info(f"function_duration{{name=\"my_function\"}} {duration}")
    return result
```

### Log Aggregation

Configure logging for aggregation:

```toml
[server]
log_level = "info"
```

Parse logs with Loki, Elasticsearch, or similar.

## Performance

### Uvicorn Workers

For multi-core utilization:

```bash
tinybase serve --workers 4
```

Or with gunicorn:

```bash
gunicorn tinybase.api.app:create_app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

!!! warning "Scheduler Consideration"
With multiple workers, ensure only one runs the scheduler to avoid duplicate executions.

### Connection Pooling

SQLite has limited connection handling. Keep worker count reasonable:

- 2-4 workers for typical workloads
- Monitor for "database is locked" errors

### Caching

For frequently accessed data:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_data(key):
    # Expensive query
    return result
```

## Security Hardening

### File Permissions

```bash
# Application files (read-only)
chmod -R 755 /opt/tinybase
chmod 644 /opt/tinybase/tinybase.toml

# Data directory (read-write for service user)
chmod 750 /var/lib/tinybase
chown tinybase:tinybase /var/lib/tinybase
```

### Network Security

```bash
# Firewall rules (ufw example)
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp  # Block direct access
```

### Secret Management

Use environment variables or secret managers:

```bash
# AWS Secrets Manager
export TINYBASE_ADMIN_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id tinybase/admin-password --query SecretString --output text)

# HashiCorp Vault
export TINYBASE_ADMIN_PASSWORD=$(vault kv get -field=password secret/tinybase)
```

## Disaster Recovery

### Backup Strategy

| Data          | Frequency       | Retention          |
| ------------- | --------------- | ------------------ |
| Database      | Every 6 hours   | 7 days             |
| Configuration | On change       | 30 days            |
| Functions     | With deployment | Version controlled |

### Recovery Procedure

1. **Stop the service**

   ```bash
   systemctl stop tinybase
   ```

1. **Restore database**

   ```bash
   cp /var/backups/tinybase/tinybase-latest.db /var/lib/tinybase/tinybase.db
   chown tinybase:tinybase /var/lib/tinybase/tinybase.db
   ```

1. **Verify integrity**

   ```bash
   sqlite3 /var/lib/tinybase/tinybase.db "PRAGMA integrity_check;"
   ```

1. **Start the service**

   ```bash
   systemctl start tinybase
   ```

1. **Verify operation**

   ```bash
   curl http://localhost:8000/docs
   ```

## Upgrades

### Zero-Downtime Upgrades

1. Deploy new version alongside old
1. Run database migrations
1. Switch traffic to new version
1. Remove old version

### Rolling Updates (Docker)

```bash
# Pull new image
docker pull tinybase:latest

# Recreate container
docker-compose up -d --force-recreate tinybase
```

### Migration Commands

```bash
# Before upgrade, backup
tinybase db backup /var/backups/pre-upgrade.db

# After upgrade, migrate
tinybase db upgrade
```

## Troubleshooting

### Common Issues

**"Database is locked"**

- Too many concurrent connections
- Long-running query blocking others
- Solution: Reduce workers, optimize queries

**"Token expired" errors**

- Clock skew between servers
- Token TTL too short
- Solution: Sync clocks (NTP), increase TTL

**High memory usage**

- Large query results
- Memory leaks in functions
- Solution: Paginate queries, monitor function code

### Debug Mode (Temporarily)

For troubleshooting only:

```bash
TINYBASE_DEBUG=true TINYBASE_LOG_LEVEL=debug tinybase serve
```

!!! danger "Never in Production"
Disable debug mode after troubleshooting. It exposes sensitive information.

## See Also

- [Docker Deployment](docker.md) - Container setup
- [Configuration](../getting-started/configuration.md) - All options
- [CLI Reference](../reference/cli.md) - Management commands
