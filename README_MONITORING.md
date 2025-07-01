# LLM Monitoring with OpenLLMetry

This project includes OpenLLMetry (Traceloop SDK) integration for monitoring and observability of AI/LLM calls.

## Features

- Automatic tracing of Google Vertex AI calls
- Performance metrics and latency tracking
- Error tracking and debugging
- OpenTelemetry-based observability

## Configuration

### Development Mode

For local development, monitoring runs with batching disabled:

```python
# Automatically detected when ENV=development
```

### Production Mode

For production, you can configure an OpenTelemetry collector:

1. Set up environment variables in `.env`:

```bash
ENV=production
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-collector.com
OTEL_API_KEY=your-api-key-here
```

2. The monitoring will automatically send traces to your configured endpoint.

### Disabling Telemetry

To opt out of Traceloop telemetry:

```bash
TRACELOOP_TELEMETRY=FALSE
```

## Viewing Traces

### Local Development

For local development, traces are logged to the console. You can use tools like:

- **Jaeger**: Run locally with Docker
  ```bash
  docker run -d --name jaeger \
    -e COLLECTOR_OTLP_ENABLED=true \
    -p 16686:16686 \
    -p 4317:4317 \
    -p 4318:4318 \
    jaegertracing/all-in-one:latest
  ```

- **SigNoz**: Open source APM
- **DataDog**: Commercial APM service
- **New Relic**: Commercial monitoring platform

### Production

Configure your preferred OpenTelemetry backend:

1. **Cloud Providers**:
   - Google Cloud Trace
   - AWS X-Ray
   - Azure Monitor

2. **Self-Hosted**:
   - Jaeger
   - Zipkin
   - Tempo

3. **Commercial**:
   - DataDog
   - New Relic
   - Splunk
   - Honeycomb

## What's Monitored

- **AI Generation Calls**:
  - Request/response latency
  - Token usage (when available)
  - Error rates
  - Model parameters

- **Performance Metrics**:
  - Subtitle generation time per chunk
  - Language processing duration
  - Overall job completion time

- **Error Tracking**:
  - API failures
  - Rate limiting
  - Authentication issues

## Troubleshooting

If monitoring is not working:

1. Check that the Traceloop SDK is installed:
   ```bash
   pip install traceloop-sdk
   ```

2. Verify initialization in logs:
   ```
   ✅ LLM monitoring initialized with OpenLLMetry
   ```

3. For production, ensure your OTLP endpoint is accessible

## Further Resources

- [OpenLLMetry Documentation](https://github.com/traceloop/openllmetry)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Vertex AI Monitoring Best Practices](https://cloud.google.com/vertex-ai/docs/monitoring)