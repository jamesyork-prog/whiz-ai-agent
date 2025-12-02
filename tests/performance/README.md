# Performance Testing

This directory contains performance testing and profiling tools for the webhook automation system.

## Overview

Performance testing ensures the webhook endpoint can handle production load with acceptable latency and reliability. This includes:

- Load testing at various traffic levels
- Performance profiling to identify bottlenecks
- Sustained load testing for stability
- Burst traffic testing for resilience

## Prerequisites

1. **Running System**: Webhook server must be running
   ```bash
   docker-compose up -d
   ```

2. **Test Configuration**: Webhook secret must match test expectations
   ```bash
   # In .env
   WEBHOOK_SECRET=test_secret_key_12345
   ```

3. **Dependencies**: All test dependencies installed in container
   ```bash
   # Already included in parlant container
   pytest
   pytest-asyncio
   httpx
   ```

## Load Testing

### Running Load Tests

All load tests should be run inside the Docker container:

```bash
# Run all load tests
docker-compose exec parlant pytest tests/performance/test_webhook_load.py -v -s

# Run specific test
docker-compose exec parlant pytest tests/performance/test_webhook_load.py::test_load_100_requests_per_minute -v -s
```

### Available Load Tests

#### 1. Standard Load Test (100 req/min)

**Test**: `test_load_100_requests_per_minute`

**Purpose**: Verify system can handle target throughput

**Metrics**:
- Total requests: 100
- Duration: ~60 seconds
- Target rate: 100 requests per minute
- Success rate: > 95%
- P95 latency: < 5 seconds

**Usage**:
```bash
docker-compose exec parlant pytest tests/performance/test_webhook_load.py::test_load_100_requests_per_minute -v -s
```

**Expected Output**:
```
============================================================
Load Test: 100 requests at 100 req/min
============================================================

Duration: 60.23 seconds
Actual rate: 1.66 req/sec

Success Rate: 100.0%
  Success: 100
  Failure: 0

Response Times (ms):
  Min:    123.45
  Mean:   234.56
  Median: 223.45
  P95:    456.78
  P99:    567.89
  Max:    678.90

Status Codes:
  200: 100
```

#### 2. Sustained Load Test (2 minutes)

**Test**: `test_load_sustained_rate`

**Purpose**: Verify no performance degradation over time

**Metrics**:
- Total requests: 200
- Duration: ~120 seconds
- Performance degradation: < 50%

**Usage**:
```bash
docker-compose exec parlant pytest tests/performance/test_webhook_load.py::test_load_sustained_rate -v -s
```

**What It Checks**:
- Response times remain consistent
- No memory leaks
- No connection pool exhaustion
- System recovers between requests

#### 3. Burst Traffic Test

**Test**: `test_load_burst_traffic`

**Purpose**: Verify system handles traffic bursts gracefully

**Metrics**:
- Burst size: 50 requests
- Burst duration: < 5 seconds
- Rate limiting: Activates correctly
- Recovery: System remains stable

**Usage**:
```bash
docker-compose exec parlant pytest tests/performance/test_webhook_load.py::test_load_burst_traffic -v -s
```

**What It Checks**:
- Rate limiting prevents overload
- Some requests succeed during burst
- System doesn't crash
- Normal processing resumes after burst

## Performance Profiling

### Running Profiler

```bash
docker-compose exec parlant python tests/performance/profile_webhook.py
```

### What It Profiles

The profiler measures time spent in different operations:

1. **Payload Generation**: Creating webhook payload
2. **Signature Generation**: HMAC-SHA256 signing
3. **HTTP Request**: Network round-trip time
4. **Response Parsing**: JSON deserialization
5. **End-to-End**: Total processing time

### Expected Output

```
======================================================================
Webhook Performance Profiling
======================================================================

Profiling 10 webhook requests...
======================================================================
Request 1/10... Status: 200
Request 2/10... Status: 200
...

======================================================================
Performance Profile Report
======================================================================

Operation                                Total (ms)   Avg (ms)    Count
----------------------------------------------------------------------
http_request_total                         2345.67     234.57       10
signature_generation                        123.45      12.35       10
payload_generation                           45.67       4.57       10
response_parsing                             23.45       2.35       10
end_to_end                                 2567.89     256.79       10
======================================================================

Bottleneck Analysis:
----------------------------------------------------------------------
⚠️  http_request_total: 91.3% of total time (avg: 234.57ms)

Metrics After Load:
======================================================================
Total webhooks: 30
Success rate: 100.0%

Processing Times:
  P50: 234.56ms
  P95: 456.78ms
  P99: 567.89ms
  Avg: 245.67ms
======================================================================
```

### Interpreting Results

**Bottlenecks** (operations > 10% of total time):
- **http_request_total**: External API latency
  - **Solution**: Enable connection pooling, add caching
  - **Expected**: 200-500ms for external APIs

- **signature_generation**: HMAC computation
  - **Solution**: Already optimized, minimal overhead
  - **Expected**: < 10ms per request

- **payload_generation**: JSON serialization
  - **Solution**: Use orjson for faster parsing
  - **Expected**: < 5ms per request

## Metrics Monitoring

### Accessing Metrics

```bash
# Get current metrics
curl http://localhost:8801/webhook/metrics | jq

# Monitor metrics continuously
watch -n 5 'curl -s http://localhost:8801/webhook/metrics | jq ".webhook_metrics"'
```

### Key Metrics

```json
{
  "webhook_metrics": {
    "success_count": 1234,
    "failure_count": 12,
    "success_rate_percent": 99.0,
    "processing_times": {
      "p50": 234.5,
      "p95": 456.7,
      "p99": 789.0,
      "average": 267.8,
      "count": 1246
    }
  },
  "performance_metrics": {
    "slow_operation_count": 5,
    "api_latencies": {
      "freshdesk": {
        "p50": 123.4,
        "p95": 234.5,
        "p99": 345.6
      }
    }
  }
}
```

## Performance Targets

| Metric | Target | Acceptable | Action Required |
|--------|--------|------------|-----------------|
| Success Rate | > 99% | > 95% | < 95% |
| P50 Latency | < 500ms | < 1000ms | > 1000ms |
| P95 Latency | < 2000ms | < 5000ms | > 5000ms |
| P99 Latency | < 5000ms | < 10000ms | > 10000ms |
| Throughput | 100 req/min | 50 req/min | < 50 req/min |

## Troubleshooting

### Tests Failing

**Symptom**: Load tests fail with connection errors

**Solutions**:
1. Verify webhook server is running:
   ```bash
   curl http://localhost:8801/webhook/health
   ```

2. Check webhook secret matches:
   ```bash
   docker-compose exec parlant env | grep WEBHOOK_SECRET
   ```

3. Review server logs:
   ```bash
   docker-compose logs -f parlant
   ```

### High Latency

**Symptom**: P95 > 5 seconds

**Solutions**:
1. Run profiler to identify bottleneck
2. Check external API latency
3. Review cache hit rates
4. Increase connection pool size

### Low Throughput

**Symptom**: Cannot sustain 100 req/min

**Solutions**:
1. Check rate limiting configuration
2. Review resource usage (CPU, memory)
3. Look for blocking operations
4. Consider horizontal scaling

### Memory Issues

**Symptom**: Container crashes during load test

**Solutions**:
1. Reduce cache sizes
2. Decrease connection pool size
3. Monitor memory usage during test
4. Increase container memory limit

## Best Practices

1. **Baseline First**: Run tests on clean system to establish baseline
2. **Isolate Changes**: Test one configuration change at a time
3. **Multiple Runs**: Run each test 3-5 times for consistency
4. **Monitor Resources**: Watch CPU, memory, network during tests
5. **Document Results**: Keep record of test results and configurations
6. **Test in Staging**: Validate performance before production
7. **Regular Testing**: Run performance tests weekly or after changes

## Custom Load Tests

### Creating Custom Tests

```python
import asyncio
from tests.performance.test_webhook_load import run_load_test

async def custom_load_test():
    """Custom load test with specific parameters."""
    results = await run_load_test(
        url="http://localhost:8801/webhook/freshdesk",
        secret="test_secret_key_12345",
        total_requests=500,  # Custom request count
        requests_per_second=5.0,  # Custom rate
        ticket_id_start=10000  # Custom ticket ID range
    )
    
    summary = results.get_summary()
    print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
    print(f"P95 Latency: {summary['response_times']['p95_ms']:.2f}ms")

# Run custom test
asyncio.run(custom_load_test())
```

### Running Custom Tests

```bash
# Create custom test file
cat > tests/performance/test_custom.py << 'EOF'
# Your custom test code here
EOF

# Run custom test
docker-compose exec parlant pytest tests/performance/test_custom.py -v -s
```

## References

- Performance Optimization Guide: `../../.kiro/specs/webhook-automation/PERFORMANCE_OPTIMIZATION.md`
- Configuration Tuning Guide: `../../.kiro/specs/webhook-automation/CONFIGURATION_TUNING.md`
- Webhook Server: `../../parlant/webhook_server.py`
- Metrics Tracker: `../../parlant/tools/metrics_tracker.py`
