import time
from typing import Dict, Any, List
from collections import defaultdict, deque
import threading
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Simple performance monitoring"""
    
    def __init__(self, max_metrics=1000):
        self.max_metrics = max_metrics
        self.metrics = {
            'requests': deque(maxlen=max_metrics),
            'processing_times': defaultdict(lambda: deque(maxlen=100)),
            'error_counts': defaultdict(int),
            'user_activity': defaultdict(int)
        }
        self.lock = threading.Lock()
    
    def record_request(self, endpoint: str, method: str, status_code: int, 
                      duration: float, user_id: str):
        """Record request metrics"""
        with self.lock:
            timestamp = datetime.now(timezone.utc)
            
            request_data = {
                'timestamp': timestamp,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'duration': duration,
                'user_id': user_id
            }
            
            self.metrics['requests'].append(request_data)
            self.metrics['processing_times'][endpoint].append(duration)
            self.metrics['user_activity'][user_id] += 1
            
            if status_code >= 400:
                self.metrics['error_counts'][f"{endpoint}:{status_code}"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self.lock:
            recent_requests = list(self.metrics['requests'])
            
            if not recent_requests:
                return {'no_data': True}
            
            # Calculate basic metrics
            total_requests = len(recent_requests)
            avg_response_time = sum(r['duration'] for r in recent_requests) / total_requests
            
            # Error rate
            error_requests = [r for r in recent_requests if r['status_code'] >= 400]
            error_rate = len(error_requests) / total_requests if total_requests > 0 else 0
            
            # Active users
            user_counts = defaultdict(int)
            for request in recent_requests[-100:]:  # Last 100 requests
                user_counts[request['user_id']] += 1
            
            return {
                'total_requests': total_requests,
                'average_response_time': round(avg_response_time, 3),
                'error_rate': round(error_rate, 3),
                'active_users': len(user_counts),
                'most_active_users': dict(sorted(user_counts.items(), 
                                                key=lambda x: x[1], reverse=True)[:5]),
                'error_counts': dict(self.metrics['error_counts'])
            }
