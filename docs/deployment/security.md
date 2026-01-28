# Security Considerations

This guide covers security best practices for production deployments of TinyBase.

## Authentication & Authorization

### Token Management

**JWT Configuration**

TinyBase uses JWT (JSON Web Tokens) for authentication. Configure token expiration and security:

```toml
[auth]
jwt_secret_key = "your-secret-key-here"  # CRITICAL: Use a strong random key
jwt_algorithm = "HS256"
jwt_access_token_expire_minutes = 1440   # 24 hours
jwt_refresh_token_expire_days = 30       # 30 days
```

**JWT Secret Key Security**

The JWT secret key is the most critical security component:

- **NEVER commit the secret to version control**
- Use a strong random value (auto-generated if not provided)
- Rotate the secret periodically (invalidates all tokens)
- Store in environment variables or secure key management systems
- Use different secrets for different environments

Generate a secure secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Token Expiration Strategy**

Configure appropriate token lifetimes:

- **Access tokens**: Short-lived (15 minutes to 24 hours)
  - Shorter for high-security environments
  - Longer for user convenience
- **Refresh tokens**: Long-lived (7 to 90 days)
  - Balance security with user experience
  - Require re-authentication after expiration

**Token Rotation and Refresh**

Implement proper token refresh flow:

```python
# Client-side example
def make_request(url, access_token, refresh_token):
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

    if response.status_code == 401:
        # Access token expired, refresh it
        refresh_response = requests.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        new_tokens = refresh_response.json()
        # Retry request with new access token
        response = requests.get(url, headers={"Authorization": f"Bearer {new_tokens['access_token']}"})

    return response
```

**Token Revocation**

All JWT tokens are tracked in the database for revocation:

- Logout revokes all user tokens
- Admin can revoke individual tokens
- Deleted tokens fail validation even if not expired
- Application tokens can be deactivated without deletion

**Internal Token Scoping**

Function subprocesses use internal tokens with limited scope (`scope="internal"`). These tokens:

- Have short expiration (default: 5 minutes)
- Are automatically managed by the system
- Carry user permissions for API callbacks
- Should not be exposed to client applications

### Password Security

TinyBase uses bcrypt for password hashing with appropriate cost factors. Best practices:

- Enforce minimum password length requirements in your application
- Consider implementing password complexity requirements
- Implement rate limiting on auth endpoints (see Rate Limiting below)
- Use HTTPS/TLS for all authentication requests

## Resource Limits

### Payload & Result Size Limits

Configure maximum sizes to prevent DoS attacks:

```toml
[functions]
max_function_payload_bytes = 10485760  # 10 MB
max_function_result_bytes = 10485760   # 10 MB
```

Adjust these limits based on your use case:

- **API endpoints**: Smaller limits (1-5 MB) for user-facing APIs
- **Data processing**: Larger limits (50-100 MB) for backend workflows
- **File processing**: Consider streaming instead of in-memory processing

### Concurrent Execution Limits

Limit concurrent function executions per user:

```toml
[functions]
max_concurrent_functions_per_user = 10
```

This prevents a single user from exhausting system resources.

### Function Timeouts

Configure execution timeouts to prevent runaway processes:

```toml
[scheduler]
scheduler_function_timeout_seconds = 1800  # 30 minutes
```

Adjust based on your function execution patterns.

## Network Security

### HTTPS/TLS Requirements

**Production deployments MUST use HTTPS/TLS for all traffic.**

TinyBase does not implement TLS termination. Use a reverse proxy:

**Nginx Example:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Caddy Example:**

```caddy
api.example.com {
    reverse_proxy localhost:8000
}
```

### CORS Configuration

Restrict allowed origins in production:

```toml
[cors]
allow_origins = ["https://app.example.com", "https://admin.example.com"]
```

Avoid using `["*"]` in production as it allows any origin to make requests.

### Network Isolation

**Function Execution:**

Functions run in subprocesses on the same host by default. For enhanced security:

- Run TinyBase in a containerized environment (Docker, Kubernetes)
- Use network policies to restrict function subprocess network access
- Consider dedicated execution environments for untrusted functions

## Function Security

### Dependency Management

Functions use inline PEP 723 dependency specifications:

```python
# /// script
# dependencies = [
#   "tinybase-sdk",
#   "requests==2.31.0",  # Pin versions for security
# ]
# ///
```

**Best Practices:**

- Pin dependency versions to avoid supply chain attacks
- Regularly update dependencies for security patches
- Review dependencies before allowing new functions
- Use private package indexes for sensitive organizations

### Code Review

Implement code review for function deployments:

- Review function code before deployment
- Check for sensitive data exposure
- Verify proper error handling
- Audit API calls and data access patterns

### Secrets Management

**Never hardcode secrets in function code.**

Use environment variables or dedicated secrets management:

```python
import os

@register(name="example")
def example(client, payload):
    api_key = os.getenv("THIRD_PARTY_API_KEY")
    # Use api_key securely
```

Configure secrets via environment variables:

```bash
export THIRD_PARTY_API_KEY="secret-value"
```

## Database Security

### Connection Security

For production, use encrypted database connections:

```toml
[database]
url = "postgresql://user:pass@host:5432/db?sslmode=require"
```

SQLite is suitable for development but consider PostgreSQL for production.

### Backup & Recovery

Implement regular database backups:

- Automated backup schedule
- Encrypted backup storage
- Tested restore procedures
- Point-in-time recovery capability

### Access Control

- Use dedicated database users with minimal privileges
- Separate read/write access where appropriate
- Implement database-level row security policies for multi-tenant deployments

## Monitoring & Logging

### Structured Logging

Enable structured logging for security event monitoring:

```toml
[functions]
function_logging_enabled = true
function_logging_level = "INFO"
function_logging_format = "json"
```

### Metrics & Alerting

Monitor security-relevant metrics:

- Failed authentication attempts
- Function execution failures
- Abnormal resource usage
- API rate limit hits

Use the metrics endpoint:

```bash
GET /api/admin/functions/metrics?hours=24
```

### Audit Logging

Function calls are automatically logged with:

- User ID
- Trigger type (manual/scheduled)
- Execution status and duration
- Error information

Query audit logs via:

```bash
GET /api/admin/functions/calls
```

## Rate Limiting

**Note:** Built-in rate limiting is not yet implemented in TinyBase MVP.

For production deployments, implement rate limiting at the reverse proxy level:

**Nginx Example:**

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://localhost:8000;
    }
}
```

**Recommended Limits:**

- Auth endpoints: 5 requests/minute per IP
- Function execution: 10 requests/second per user
- List endpoints: 100 requests/minute per user

## Container Security

### Docker Best Practices

When deploying with Docker:

```dockerfile
# Use non-root user
RUN useradd -m -u 1000 tinybase
USER tinybase

# Minimal base image
FROM python:3.11-slim

# Read-only root filesystem where possible
docker run --read-only --tmpfs /tmp tinybase
```

### Resource Limits

Set container resource limits:

```yaml
# docker-compose.yml
services:
  tinybase:
    image: tinybase:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          memory: 512M
```

## Compliance Considerations

### Data Privacy

- Implement data retention policies
- Support data deletion requests (GDPR, CCPA)
- Encrypt sensitive data at rest and in transit
- Document data collection and usage

### Audit Requirements

TinyBase provides:

- Function call audit trail
- User action logging
- Authentication event tracking
- Configuration change tracking (via git)

Export audit logs regularly for compliance reporting.

## Security Checklist

Before deploying to production:

- [ ] HTTPS/TLS configured via reverse proxy
- [ ] CORS restricted to specific origins
- [ ] Auth token TTL configured appropriately
- [ ] Resource limits configured (payload, result, concurrent)
- [ ] Function timeouts set
- [ ] Secrets managed via environment variables
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Rate limiting implemented at proxy
- [ ] Security updates applied
- [ ] Audit logging enabled
- [ ] Function code review process in place

## Reporting Security Issues

If you discover a security vulnerability in TinyBase, please report it to:

- **Email:** <security@tinybase.example.com> (update with actual contact)
- **Private disclosure:** Use GitHub Security Advisories

Do not publicly disclose security issues until a fix is available.

## Updates & Patches

- Subscribe to TinyBase security announcements
- Apply security patches promptly
- Test updates in staging before production
- Maintain a rollback plan

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLModel Security](https://sqlmodel.tiangolo.com/tutorial/where/)
