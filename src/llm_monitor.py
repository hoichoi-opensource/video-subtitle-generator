"""
LLM Monitoring Setup with OpenLLMetry
Provides observability for Google Gemini AI calls
"""

import os

# Try to import traceloop - it's optional
try:
    from traceloop.sdk import Traceloop
    TRACELOOP_AVAILABLE = True
except ImportError:
    TRACELOOP_AVAILABLE = False
    print("⚠️  traceloop-sdk not installed - LLM monitoring disabled")


def init_monitoring():
    """Initialize OpenLLMetry monitoring for LLM calls"""
    
    if not TRACELOOP_AVAILABLE:
        print("⚠️  LLM monitoring skipped - traceloop-sdk not available")
        return
    
    # Initialize Traceloop SDK
    # You can configure it to send data to different backends
    # For local development, disable batching
    try:
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
    except Exception as e:
        print(f"⚠️  Failed to initialize LLM monitoring: {e}")


def shutdown_monitoring():
    """Shutdown monitoring gracefully"""
    # The SDK handles shutdown automatically, but you can add custom logic here
    pass