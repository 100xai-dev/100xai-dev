# Docker Security Guidelines

## Overview
This document outlines security measures implemented to prevent sensitive data from being included in Docker images.

## Critical Security Protections

### 1. .dockerignore Files
- **Root `.dockerignore`**: Comprehensive exclusion rules for the entire project
- **Backend `.dockerignore`**: Additional backend-specific exclusions
- **Purpose**: Prevent sensitive files from being copied into Docker images

### 2. Excluded Sensitive Files

#### Environment Files and Secrets
- `.env`, `.env.*` files containing API keys and database credentials
- SSH keys, certificates, and other cryptographic material
- Secret management directories

#### Development Files  
- `venv/` virtual environments
- Test files with hardcoded credentials
- Operations scripts with sensitive URLs/tokens
- Development databases (`dev.db`)

#### Documentation with Setup Information
- Integration guides with OAuth secrets
- Setup scripts with hardcoded configuration

### 3. Production Security Recommendations

#### Environment Variables
Use environment variables instead of `.env` files in production:
```bash
docker run -e DATABASE_URL=... -e JWT_SECRET=... your-image
```

#### Secrets Management
For production deployments, use proper secrets management:
- Docker Secrets (Docker Swarm)
- Kubernetes Secrets
- HashiCorp Vault
- Cloud provider secret managers (AWS Secrets Manager, Azure Key Vault, etc.)

#### Image Scanning
Regularly scan built images for:
- Exposed secrets
- Security vulnerabilities
- Unnecessary files

```bash
# Example using Docker Scout
docker scout cves your-image:latest

# Example using Trivy
trivy image your-image:latest
```

### 4. Build Verification

Before pushing images to registries, verify no sensitive data is included:

```bash
# Build the image
docker build -t your-image .

# Run a container and check for sensitive files
docker run --rm -it your-image /bin/bash
# Inside container:
find / -name ".env*" 2>/dev/null
find / -name "*.key" 2>/dev/null
find / -name "dev.db" 2>/dev/null
```

### 5. CI/CD Security

In GitHub Actions or other CI systems:
- Never build images with production secrets
- Use separate secrets management for production deployments
- Scan images before pushing to registries
- Use multi-stage builds to exclude build dependencies

### 6. Multi-stage Build Example (Advanced)

For even better security, consider multi-stage builds:

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app/ ./app/
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "app/main.py"]
```

## Security Checklist

Before deploying Docker images:

- [ ] Verified `.dockerignore` excludes all sensitive files
- [ ] No `.env` files in the image
- [ ] No development databases or logs
- [ ] No SSH keys or certificates
- [ ] No hardcoded secrets in source code
- [ ] Environment variables used for configuration
- [ ] Image scanned for vulnerabilities
- [ ] Build context minimized
- [ ] Run as non-root user (optional but recommended)

## Emergency Response

If sensitive data is accidentally included in a pushed image:
1. **Immediately rotate** all exposed secrets
2. **Remove** the compromised image from registries
3. **Rebuild and redeploy** with proper exclusions
4. **Audit** access logs for potential unauthorized access
5. **Update** security procedures to prevent recurrence