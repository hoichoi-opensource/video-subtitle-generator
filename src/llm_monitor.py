"""
LLM Monitoring Setup with OpenLLMetry
Provides observability for Google Gemini AI calls
"""

import os
from traceloop.sdk import Traceloop


def init_monitoring():
    """Initialize OpenLLMetry monitoring for LLM calls"""
    
    # Initialize Traceloop SDK
    # You can configure it to send data to different backends
    # For local development, disable batching
    if os.getenv("ENV", "production") == "development":
        Traceloop.init(
            disable_batch=True,
            # You can add more config options here
            # For example, to send to a specific backend:
            # endpoint="https://your-otel-collector.com",
            # headers={"Authorization": "Bearer YOUR_API_KEY"}
        )
    else:
        Traceloop.init(
            # Production configuration
            # You might want to send to an OpenTelemetry collector
            # endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            # headers={"Authorization": f"Bearer {os.getenv('OTEL_API_KEY')}"}
        )
    
    print("✅ LLM monitoring initialized with OpenLLMetry")


def shutdown_monitoring():
    """Shutdown monitoring gracefully"""
    # The SDK handles shutdown automatically, but you can add custom logic here
    pass