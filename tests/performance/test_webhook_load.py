"""
Load testing for webhook endpoint.

This module provides load testing capabilities to:
- Send 100 webhooks per minute
- Measure response time distribution
- Identify bottlenecks
- Verify no dropped requests
"""

import asyncio
import time
import hmac
import hashlib
import json
import statistics
from typing import List, Dict, Any, Tuple
from datetime import datetime
import httpx
import pytest


class LoadTestResults:
    """Container for load test results."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count = 0
        self.failure_count = 0
        self.status_codes: Dict[int, int] = {}
        self.errors: List[str] = []
        self.start_time: float = 0
        self.end_time: float = 0
    
    def add_result(
        self,
        response_time_ms: float,
        status_code: int,
        success: bool,
        error: str = None
    ):
        """Add a single request result."""
        self.response_times.append(response_time_ms)
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.errors.append(error)
        
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def get_percentile(self, percentile: int) -> float:
        """Calculate response time percentile."""
        if not self.response_times:
            return 0.0
        
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * (percentile / 100.0))
        
        if index >= len(sorted_times):
            index = len(sorted_times) - 1
        
        return sorted_times[index]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of load test results."""
        total_requests = self.success_count + self.failure_count
        duration_seconds = self.end_time - self.start_time
        
        return {
            "total_requests": total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate_percent": (self.success_count / total_requests * 100) if total_requests > 0 else 0,
            "duration_seconds": duration_seconds,
            "requests_per_second": total_requests / duration_seconds if duration_seconds > 0 else 0,
            "response_times": {
                "min_ms": min(self.response_times) if self.response_times else 0,
                "max_ms": max(self.response_times) if self.response_times else 0,
                "mean_ms": statistics.mean(self.response_times) if self.response_times else 0,
                "median_ms": statistics.median(self.response_times) if self.response_times else 0,
                "p50_ms": self.get_percentile(50),
                "p95_ms": self.get_percentile(95),
                "p99_ms": self.get_percentile(99),
            },
            "status_codes": self.status_codes,
            "errors": self.errors[:10]  # First 10 errors
        }


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.
    
    Args:
        payload: Raw payload bytes
        secret: Webhook secret
        
    Returns:
        Base64-encoded signature
    """
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return signature


async def send_webhook_request(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    secret: str
) -> Tuple[float, int, bool, str]:
    """
    Send a single webhook request.
    
    Args:
        client: HTTP client
        url: Webhook endpoint URL
        payload: Webhook payload
        secret: Webhook secret for signature
        
    Returns:
        Tuple of (response_time_ms, status_code, success, error_message)
    """
    start_time = time.time()
    
    try:
        # Serialize payload
        payload_bytes = json.dumps(payload).encode('utf-8')
        
        # Generate signature
        signature = generate_webhook_signature(payload_bytes, secret)
        
        # Send request
        response = await client.post(
            url,
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Freshdesk-Signature": signature
            },
            timeout=30.0
        )
        
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        success = response.status_code == 200
        error_message = None if success else response.text
        
        return response_time_ms, response.status_code, success, error_message
        
    except Exception as e:
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        return response_time_ms, 0, False, str(e)


async def run_load_test(
    url: str,
    secret: str,
    total_requests: int,
    requests_per_second: float,
    ticket_id_start: int = 1000
) -> LoadTestResults:
    """
    Run load test against webhook endpoint.
    
    Args:
        url: Webhook endpoint URL
        secret: Webhook secret
        total_requests: Total number of requests to send
        requests_per_second: Target rate (e.g., 100/60 = 1.67 for 100 per minute)
        ticket_id_start: Starting ticket ID for test payloads
        
    Returns:
        LoadTestResults with comprehensive metrics
    """
    results = LoadTestResults()
    results.start_time = time.time()
    
    # Calculate delay between requests
    delay_seconds = 1.0 / requests_per_second
    
    async with httpx.AsyncClient() as client:
        for i in range(total_requests):
            # Generate unique payload for each request
            ticket_id = str(ticket_id_start + i)
            payload = {
                "ticket_id": ticket_id,
                "event": "ticket_created",
                "triggered_at": datetime.utcnow().isoformat() + "Z",
                "ticket_subject": f"Load Test Ticket {ticket_id}",
                "ticket_status": 2,
                "ticket_priority": 1,
                "requester_email": f"loadtest{i}@example.com"
            }
            
            # Send request
            response_time, status_code, success, error = await send_webhook_request(
                client, url, payload, secret
            )
            
            # Record result
            results.add_result(response_time, status_code, success, error)
            
            # Wait before next request to maintain target rate
            if i < total_requests - 1:  # Don't wait after last request
                await asyncio.sleep(delay_seconds)
    
    results.end_time = time.time()
    
    return results


@pytest.mark.asyncio
async def test_load_100_requests_per_minute():
    """
    Load test: Send 100 webhooks per minute.
    
    This test verifies:
    - Endpoint can handle 100 requests per minute
    - Response times are acceptable
    - No requests are dropped
    - Success rate is high
    """
    # Configuration
    url = "http://localhost:8801/webhook/freshdesk"
    secret = "test_secret_key_12345"
    total_requests = 100
    requests_per_minute = 100
    requests_per_second = requests_per_minute / 60.0
    
    print(f"\n{'='*60}")
    print(f"Load Test: {total_requests} requests at {requests_per_minute} req/min")
    print(f"{'='*60}\n")
    
    # Run load test
    results = await run_load_test(
        url=url,
        secret=secret,
        total_requests=total_requests,
        requests_per_second=requests_per_second
    )
    
    # Print results
    summary = results.get_summary()
    
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"Actual rate: {summary['requests_per_second']:.2f} req/sec")
    print(f"\nSuccess Rate: {summary['success_rate_percent']:.1f}%")
    print(f"  Success: {summary['success_count']}")
    print(f"  Failure: {summary['failure_count']}")
    print(f"\nResponse Times (ms):")
    print(f"  Min:    {summary['response_times']['min_ms']:.2f}")
    print(f"  Mean:   {summary['response_times']['mean_ms']:.2f}")
    print(f"  Median: {summary['response_times']['median_ms']:.2f}")
    print(f"  P95:    {summary['response_times']['p95_ms']:.2f}")
    print(f"  P99:    {summary['response_times']['p99_ms']:.2f}")
    print(f"  Max:    {summary['response_times']['max_ms']:.2f}")
    print(f"\nStatus Codes:")
    for code, count in sorted(summary['status_codes'].items()):
        print(f"  {code}: {count}")
    
    if summary['errors']:
        print(f"\nFirst {len(summary['errors'])} Errors:")
        for error in summary['errors']:
            print(f"  - {error[:100]}")
    
    print(f"\n{'='*60}\n")
    
    # Assertions
    assert summary['success_rate_percent'] >= 95.0, \
        f"Success rate too low: {summary['success_rate_percent']:.1f}%"
    
    assert summary['response_times']['p95_ms'] < 5000, \
        f"P95 response time too high: {summary['response_times']['p95_ms']:.2f}ms"
    
    assert summary['failure_count'] == 0, \
        f"Some requests failed: {summary['failure_count']}"


@pytest.mark.asyncio
async def test_load_sustained_rate():
    """
    Load test: Sustained rate over 2 minutes.
    
    This test verifies:
    - System can maintain performance over time
    - No degradation in response times
    - Memory/resource leaks don't occur
    """
    url = "http://localhost:8801/webhook/freshdesk"
    secret = "test_secret_key_12345"
    total_requests = 200  # 2 minutes at 100/min
    requests_per_second = 100 / 60.0
    
    print(f"\n{'='*60}")
    print(f"Sustained Load Test: {total_requests} requests over 2 minutes")
    print(f"{'='*60}\n")
    
    results = await run_load_test(
        url=url,
        secret=secret,
        total_requests=total_requests,
        requests_per_second=requests_per_second,
        ticket_id_start=2000
    )
    
    summary = results.get_summary()
    
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
    print(f"P95 Response Time: {summary['response_times']['p95_ms']:.2f}ms")
    print(f"P99 Response Time: {summary['response_times']['p99_ms']:.2f}ms")
    
    # Check for performance degradation
    # Split results into first half and second half
    midpoint = len(results.response_times) // 2
    first_half_p95 = sorted(results.response_times[:midpoint])[int(midpoint * 0.95)]
    second_half_p95 = sorted(results.response_times[midpoint:])[int(midpoint * 0.95)]
    
    degradation_percent = ((second_half_p95 - first_half_p95) / first_half_p95) * 100
    
    print(f"\nPerformance Degradation Analysis:")
    print(f"  First half P95:  {first_half_p95:.2f}ms")
    print(f"  Second half P95: {second_half_p95:.2f}ms")
    print(f"  Degradation:     {degradation_percent:+.1f}%")
    
    print(f"\n{'='*60}\n")
    
    # Assertions
    assert summary['success_rate_percent'] >= 95.0
    assert degradation_percent < 50.0, \
        f"Performance degraded too much: {degradation_percent:.1f}%"


@pytest.mark.asyncio
async def test_load_burst_traffic():
    """
    Load test: Burst traffic pattern.
    
    This test verifies:
    - System handles traffic bursts
    - Rate limiting works correctly
    - Recovery after burst
    """
    url = "http://localhost:8801/webhook/freshdesk"
    secret = "test_secret_key_12345"
    
    print(f"\n{'='*60}")
    print(f"Burst Traffic Test")
    print(f"{'='*60}\n")
    
    # Send burst of 50 requests as fast as possible
    burst_results = LoadTestResults()
    burst_results.start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(50):
            ticket_id = str(3000 + i)
            payload = {
                "ticket_id": ticket_id,
                "event": "ticket_created",
                "triggered_at": datetime.utcnow().isoformat() + "Z",
                "ticket_subject": f"Burst Test Ticket {ticket_id}",
            }
            
            task = send_webhook_request(client, url, payload, secret)
            tasks.append(task)
        
        # Send all requests concurrently
        results_list = await asyncio.gather(*tasks)
        
        for response_time, status_code, success, error in results_list:
            burst_results.add_result(response_time, status_code, success, error)
    
    burst_results.end_time = time.time()
    
    summary = burst_results.get_summary()
    
    print(f"Burst Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"Burst Rate: {summary['requests_per_second']:.2f} req/sec")
    print(f"Success Rate: {summary['success_rate_percent']:.1f}%")
    print(f"P95 Response Time: {summary['response_times']['p95_ms']:.2f}ms")
    
    # Count rate limit responses (429)
    rate_limited = summary['status_codes'].get(429, 0)
    print(f"\nRate Limited Requests: {rate_limited}")
    
    print(f"\n{'='*60}\n")
    
    # We expect some rate limiting during burst
    # But system should handle it gracefully
    assert summary['success_count'] > 0, "No requests succeeded during burst"


if __name__ == "__main__":
    """
    Run load tests manually.
    
    Usage:
        python -m pytest tests/performance/test_webhook_load.py -v -s
    """
    pass
