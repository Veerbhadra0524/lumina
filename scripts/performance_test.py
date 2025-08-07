import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor
import json

BASE_URL = "http://localhost:5000"

def test_query_performance(query_text: str = "What is machine learning?"):
    """Test single query performance"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"query": query_text},
            timeout=30
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            'duration': duration,
            'status_code': response.status_code,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {
            'duration': time.time() - start_time,
            'status_code': 0,
            'success': False,
            'error': str(e)
        }

def load_test(num_requests: int = 50, num_threads: int = 10):
    """Perform load testing"""
    print(f"Starting load test: {num_requests} requests with {num_threads} threads")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        
        for i in range(num_requests):
            future = executor.submit(test_query_performance, f"Test query {i}")
            futures.append(future)
        
        for future in futures:
            result = future.result()
            results.append(result)
            print(f"Request completed in {result['duration']:.2f}s - Status: {result['status_code']}")
    
    # Analyze results
    successful_results = [r for r in results if r['success']]
    durations = [r['duration'] for r in successful_results]
    
    if durations:
        print(f"\n=== Load Test Results ===")
        print(f"Total Requests: {num_requests}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(results) - len(successful_results)}")
        print(f"Success Rate: {len(successful_results)/len(results)*100:.1f}%")
        print(f"Average Response Time: {statistics.mean(durations):.2f}s")
        print(f"Median Response Time: {statistics.median(durations):.2f}s")
        print(f"Min Response Time: {min(durations):.2f}s")
        print(f"Max Response Time: {max(durations):.2f}s")
        
        if len(durations) > 1:
            print(f"StdDev: {statistics.stdev(durations):.2f}s")
    else:
        print("No successful requests!")

def test_health_endpoint():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health Check: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    print("=== Lumina RAG Performance Tests ===\n")
    
    # Test health first
    test_health_endpoint()
    print()
    
    # Single request test
    print("Testing single request...")
    result = test_query_performance()
    print(f"Single request: {result['duration']:.2f}s - Status: {result['status_code']}")
    print()
    
    # Load test
    load_test(num_requests=20, num_threads=5)
