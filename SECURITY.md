# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainer with details of the vulnerability
3. Include steps to reproduce, impact assessment, and suggested fixes if possible

We will respond within 48 hours and work with you to address the issue.

---

## Security Best Practices

### Deployment Security

#### 1. **API Key Management**
- **Never** commit `.env` files to version control
- Use strong, randomly generated API keys (minimum 32 characters)
- Rotate API keys regularly (recommended: every 90 days)
- Use different API keys for development, staging, and production

```bash
# Generate a strong API key
openssl rand -hex 32
```

#### 2. **Environment Variables**
Required environment variables:
- `GEMINI_API_KEY` - Your Google Gemini API key
- `SERVER_API_KEY` - API key for authenticating requests to your server
- `ALLOWED_ORIGINS` - Comma-separated list of allowed CORS origins
- `RATE_LIMIT` - Rate limit (e.g., "10/minute")

#### 3. **CORS Configuration**
- **Never** use `allow_origins=["*"]` in production
- Specify exact origins that should access your API
- Keep `allow_credentials=False` unless absolutely necessary

Example:
```bash
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

#### 4. **Rate Limiting**
- Adjust rate limits based on your use case
- Monitor rate limit violations in logs
- Consider implementing per-user rate limiting for multi-tenant scenarios

#### 5. **HTTPS Only**
- **Always** use HTTPS in production
- Configure your reverse proxy (nginx, Caddy) to enforce HTTPS
- Enable HSTS headers (already configured in the app)

#### 6. **Docker Security**
- The application runs as non-root user `appuser`
- Keep base images updated
- Scan images for vulnerabilities regularly

```bash
# Scan Docker image
docker scan gemini-api-server
```

---

## Security Features

### Authentication
- API key authentication via `X-API-Key` header
- All endpoints except `/health` require authentication

### SSRF Protection
- URL validation before fetching external resources
- Blocked: localhost, private IPs, cloud metadata endpoints
- Only HTTP/HTTPS schemes allowed

### Input Validation
- Pydantic models with strict validation
- Maximum field lengths enforced
- Enum validation for categorical fields
- Custom validators for business logic

### Rate Limiting
- Configurable rate limiting per IP address
- Default: 10 requests per minute
- Returns 429 status code when limit exceeded

### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HTTPS only)
- `Content-Security-Policy: default-src 'self'`

### Error Handling
- Generic error messages to clients
- Detailed errors logged server-side only
- No stack traces or internal paths exposed

---

## Security Checklist

Before deploying to production:

- [ ] Set strong `SERVER_API_KEY` (32+ characters)
- [ ] Configure specific `ALLOWED_ORIGINS` (not `*`)
- [ ] Set appropriate `RATE_LIMIT` for your use case
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Review and adjust file size limits if needed
- [ ] Set up log monitoring and alerting
- [ ] Configure firewall rules
- [ ] Run security scans (`bandit`, `safety`)
- [ ] Review Docker image for vulnerabilities
- [ ] Set up automated dependency updates
- [ ] Configure backup and disaster recovery
- [ ] Document incident response procedures

---

## Monitoring and Logging

### What to Monitor
1. **Failed authentication attempts** - Potential brute force attacks
2. **Rate limit violations** - Potential DoS attempts
3. **SSRF attempts** - Blocked private IP/localhost access
4. **Input validation failures** - Potential injection attempts
5. **Error rates** - Application health
6. **Response times** - Performance degradation

### Log Analysis
The application logs important security events:
```
WARNING - Blocked URL attempt: http://169.254.169.254/
WARNING - Invalid API key attempt from client
INFO - [3-pro] mode=structured thinking_level=HIGH tokens=100/200/300
```

Set up log aggregation (ELK, Splunk, CloudWatch) and alerting for security events.

---

## Compliance Considerations

### Data Privacy
- This API processes user prompts and may handle sensitive data
- Ensure compliance with GDPR, CCPA, or other applicable regulations
- Implement data retention policies
- Consider encryption at rest for stored data
- Review Google's Gemini API terms of service

### Audit Trail
- All requests are logged with timestamps
- Consider implementing request ID tracking
- Maintain logs for compliance requirements (typically 90-365 days)

---

## Incident Response

### If a Security Breach Occurs

1. **Immediate Actions**
   - Rotate all API keys immediately
   - Review logs for unauthorized access
   - Identify scope of breach

2. **Investigation**
   - Preserve logs and evidence
   - Determine attack vector
   - Assess data exposure

3. **Remediation**
   - Apply security patches
   - Update configurations
   - Implement additional controls

4. **Communication**
   - Notify affected users if applicable
   - Report to authorities if required
   - Document lessons learned

---

## Security Updates

### Dependency Management
```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade -r requirements.txt
```

### Regular Security Tasks
- **Weekly**: Review security logs
- **Monthly**: Update dependencies, run security scans
- **Quarterly**: Rotate API keys, security audit
- **Annually**: Penetration testing, compliance review

---

## Contact

For security concerns, contact: [your-email@example.com]

Last updated: 2025-12-23
