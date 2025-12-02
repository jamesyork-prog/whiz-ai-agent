"""
Performance profiling for webhook endpoint.

This script profiles webhook processing to identify bottlenecks:
- Function-level timing
- API call latency
- Database operations
- Journey execution time
"""

import asyncio
import time
import hmac
import hashlib
import json
from typing import Dict, Any
from datetime import datetime
import httpx
from contextlib import contextmanager


class PerformanceProfiler:
    """Simple performance profiler for identifying bottlenecks."""
    
    def __init__(self):
        self.timings: Dict[str, list] = {}
        self.call_counts: Dict[str, int] = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Context manager for measuring operation time."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            if operation_name not in self.timings:
                self.timings[operation_name] = []
                self.call_counts[operation_name] = 0
            
            self.timings[operation_name].append(duration_ms)
            self.call_counts[operation_name] += 1
    
    def get_report(self) -> str:
        """Generate performance report."""
        lines = [
            "\n" + "="*70,
            "Performance Profile Report",
            "="*70,
            ""
        ]
        
        # Sort by total time (sum of all calls)
        operations = []
        for op_name in self.timings:
            total_time = sum(self.timings[op_name])
            avg_time = total_time / len(self.timings[op_name])
            count = self.call_counts[op_name]
            operations.append((op_name, total_time, avg_time, count))
        
        operations.sort(key=lambda x: x[1], reverse=True)
        
        lines.append(f"{'Operation':<40} {'Total (ms)':>10} {'Avg (ms)':>10} {'Count':>8}")
        lines.append("-" * 70)
        
        for op_name, total_time, avg_time, count in operations:
            lines.append(f"{op_name:<40} {total_time:>10.2f} {avg_time:>10.2f} {count:>8}")
        
        lines.append("="*70 + "\n")
        
        return "\n".join(lines)


def generate_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature."""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return signature


async def profile_single_request(profiler: PerformanceProfiler):
    """Profile a single webhook request end-to-end."""
    
    url = "http://localhost:8801/webhook/freshdesk"
    secret = "test_secret_key_12345"
    
    # Generate payload
    with profiler.measure("payload_generation"):
        payload = {
            "ticket_id": "12345",
            "event": "ticket_created",
            "triggered_at": datetime.utcnow().isoformat() + "Z",
            "ticket_subject": "Profile Test Ticket",
            "ticket_status": 2,
            "ticket_priority": 1,
            "requester_email": "profile@example.com"
        }
        payload_bytes = json.dumps(payload).encode('utf-8')
    
    # Generate signature
    with profiler.measure("signature_generation"):
        signature = generate_webhook_signature(payload_bytes, secret)
    
    # Send request
    async with httpx.AsyncClient() as client:
        with profiler.measure("http_request_total"):
            try:
                response = await client.post(
                    url,
                    content=payload_bytes,
                    headers={
                        "Content-Type": "application/json",
                        "X-Freshdesk-Signature": signature
                    },
                    timeout=30.0
                )
                
                with profiler.measure("response_parsing"):
                    response_data = response.json()
                
                return response.status_code, response_data
                
            except Exception as e:
                print(f"Error: {e}")
                return 0, {"error": str(e)}


async def run_profiling(num_requests: int = 10):
    """
    Run profiling for multiple requests.
    
    Args:
        num_requests: Number of requests to profile
    """
    profiler = PerformanceProfiler()
    
    print(f"\nProfiling {num_requests} webhook requests...")
    print("="*70)
    
    for i in range(num_requests):
        print(f"Request {i+1}/{num_requests}...", end=" ")
        
        with profiler.measure("end_to_end"):
            status_code, response = await profile_single_request(profiler)
        
        print(f"Status: {status_code}")
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    # Print report
    print(profiler.get_report())
    
    # Identify bottlenecks
    print("\nBottleneck Analysis:")
    print("-" * 70)
    
    # Find operations taking > 10% of total time
    total_time = sum(sum(times) for times in profiler.timings.values())
    
    for op_name, times in profiler.timings.items():
        op_total = sum(times)
        percentage = (op_total / total_time) * 100
        
        if percentage > 10:
            avg_time = op_total / len(times)
            print(f"⚠️  {op_name}: {percentage:.1f}% of total time (avg: {avg_time:.2f}ms)")
    
    print("="*70 + "\n")


async def profile_with_metrics():
    """Profile webhook with metrics endpoint."""
    
    print("\nFetching metrics before load...")
    
    async with httpx.AsyncClient() as client:
        # Get initial metrics
        response = await client.get("http://localhost:8801/webhook/metrics")
        metrics_before = response.json()
        
        print(f"Initial webhook count: {metrics_before['webhook_metrics']['success_count']}")
        
        # Run some requests
        print("\nSending 20 requests...")
        for i in range(20):
            payload = {
                "ticket_id": str(5000 + i),
                "event": "ticket_created",
                "triggered_at": datetime.utcnow().isoformat() + "Z",
                "ticket_subject": f"Metrics Test {i}",
            }
            
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, "test_secret_key_12345")
            
            await client.post(
                "http://localhost:8801/webhook/freshdesk",
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Freshdesk-Signature": signature
                }
            )
        
        # Get final metrics
        response = await client.get("http://localhost:8801/webhook/metrics")
        metrics_after = response.json()
        
        print("\nMetrics After Load:")
        print("="*70)
        print(f"Total webhooks: {metrics_after['webhook_metrics']['success_count']}")
        print(f"Success rate: {metrics_after['webhook_metrics']['success_rate_percent']:.1f}%")
        
        processing_times = metrics_after['webhook_metrics']['processing_times']
        print(f"\nProcessing Times:")
        print(f"  P50: {processing_times['p50']:.2f}ms")
        print(f"  P95: {processing_times['p95']:.2f}ms")
        print(f"  P99: {processing_times['p99']:.2f}ms")
        print(f"  Avg: {processing_times['average']:.2f}ms")
        
        if metrics_after['performance_metrics']['slow_operation_count'] > 0:
            print(f"\n⚠️  Slow operations detected: {metrics_after['performance_metrics']['slow_operation_count']}")
        
        print("="*70 + "\n")


if __name__ == "__main__":
    """
    Run performance profiling.
    
    Usage:
        python tests/performance/profile_webhook.py
    """
    print("\n" + "="*70)
    print("Webhook Performance Profiling")
    print("="*70)
    
    # Run basic profiling
    asyncio.run(run_profiling(num_requests=10))
    
    # Run metrics-based profiling
    asyncio.run(profile_with_metrics())
    
    print("\nProfiling complete!")
    print("\nRecommendations:")
    print("- Operations taking >100ms should be optimized")
    print("- Consider caching for repeated operations")
    print("- Use connection pooling for external APIs")
    print("- Monitor P95/P99 latencies in production")
