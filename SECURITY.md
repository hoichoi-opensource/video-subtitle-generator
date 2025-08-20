# Security Guidelines for Video Subtitle Generator

## 🚨 CRITICAL SECURITY ALERT

**WARNING**: A service account credential file was found exposed in this repository. This has been addressed but requires immediate action.

## Immediate Actions Required

### 1. Rotate Compromised Credentials
If you cloned this repository with the exposed `service-account.json`:

1. **Go to Google Cloud Console**
2. **Navigate to IAM & Admin > Service Accounts**
3. **Find your service account: `your-service-account@your-project-id.iam.gserviceaccount.com`**
4. **Delete or disable the existing key**
5. **Generate a new key**
6. **Update your local configuration**

### 2. Secure Credential Setup

#### Method 1: Environment Variables (Recommended for Production)
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
export GCP_PROJECT_ID="your-project-id"
```

#### Method 2: Service Account File (Development)
1. Place your service account file **outside** the repository
2. Update `config/config.yaml`:
```yaml
gcp:
  service_account_path: "/secure/path/to/service-account.json"
  project_id: "your-project-id"
```

#### Method 3: Application Default Credentials
```bash
gcloud auth application-default login
```

## Security Features Implemented

### ✅ Input Validation
- **Path Traversal Protection**: Comprehensive validation against directory traversal attacks
- **File Type Validation**: MIME type and extension validation
- **Size Limits**: Configurable limits prevent resource exhaustion
- **Video Integrity**: FFmpeg-based validation prevents malicious files

### ✅ Authentication & Authorization
- **Multiple Auth Methods**: Service account, ADC, and environment variable support
- **Credential Validation**: Existence and access checks before processing
- **Error Classification**: Proper authentication error handling

### ✅ Resource Management
- **Memory Monitoring**: Automatic tracking with configurable thresholds
- **Disk Space Management**: Cleanup policies for temporary files
- **Cloud Resource Cleanup**: Automatic GCS resource management
- **Rate Limiting**: Circuit breakers and exponential backoff

### ✅ Error Handling
- **Structured Exceptions**: Comprehensive error hierarchy
- **Context Preservation**: Errors include debugging context without secrets
- **Fail-Safe Defaults**: Graceful degradation and fallback mechanisms

### ✅ Logging & Monitoring
- **Structured Logging**: JSON-formatted logs with sanitized content
- **Performance Tracking**: Detailed metrics without sensitive data
- **Health Monitoring**: Multi-level system health checks

## Security Configuration

### Required Service Account Permissions
Your service account needs these IAM roles:
- **Vertex AI User** - For AI model access
- **Storage Admin** - For GCS bucket operations
- **Service Account User** - For service account operations

### Recommended Security Settings

#### 1. Network Security
```yaml
# In production, restrict network access
gcp:
  location: "us-central1"  # Use specific regions
  bucket_mode: "use_existing"  # Use pre-configured buckets
```

#### 2. Resource Limits
```yaml
processing:
  max_file_size_gb: 10  # Adjust based on needs
  parallel_workers: 4   # Limit concurrent processing
  max_retries: 3        # Prevent infinite loops
```

#### 3. Monitoring Configuration
```yaml
system:
  log_level: "INFO"     # Avoid DEBUG in production
  max_file_size_gb: 50  # Production limits
```

## Security Best Practices

### 🔐 Credential Management
- **Never commit credentials** to version control
- **Use environment variables** for sensitive configuration
- **Rotate credentials regularly** (every 90 days)
- **Use least privilege principle** for service accounts
- **Monitor credential usage** in Google Cloud Console

### 🛡️ Infrastructure Security
- **Use VPC firewall rules** to restrict access
- **Enable Cloud Audit Logs** for compliance
- **Set up monitoring alerts** for unusual activity
- **Use Cloud KMS** for additional encryption needs

### 📊 Monitoring & Alerting
```bash
# Set up monitoring for:
- Failed authentication attempts
- Unusual resource consumption
- Error rate spikes
- Large file uploads
```

## Production Deployment Security

### Container Security
```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Set secure file permissions
COPY --chown=appuser:appuser . /app
RUN chmod 750 /app
```

### Kubernetes Security
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  capabilities:
    drop:
    - ALL
```

### Environment Variables
```yaml
env:
- name: GOOGLE_APPLICATION_CREDENTIALS
  valueFrom:
    secretKeyRef:
      name: gcp-credentials
      key: service-account.json
```

## Incident Response

If you suspect a security breach:

1. **Immediate Actions**:
   - Rotate all credentials
   - Check Google Cloud audit logs
   - Review billing for unusual activity

2. **Investigation**:
   - Check application logs for anomalies
   - Review network access patterns
   - Verify resource usage

3. **Recovery**:
   - Update security configurations
   - Apply additional monitoring
   - Document lessons learned

## Security Contact

For security issues, contact:
- **Internal**: Security team
- **External**: Create a private GitHub issue

## Regular Security Tasks

### Weekly
- [ ] Review application logs for anomalies
- [ ] Check resource usage patterns
- [ ] Verify credential rotation schedule

### Monthly
- [ ] Review and update dependencies
- [ ] Security configuration audit
- [ ] Performance security baseline

### Quarterly
- [ ] Credential rotation
- [ ] Security training updates
- [ ] Penetration testing review

## Compliance Considerations

This application handles:
- **Video content** (potentially sensitive)
- **Cloud resources** (cost implications)
- **AI processing** (privacy considerations)

Ensure compliance with:
- Data protection regulations (GDPR, CCPA)
- Industry standards (SOC 2, ISO 27001)
- Company security policies