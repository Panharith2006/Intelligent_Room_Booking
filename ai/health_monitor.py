# ai/health_monitor.py

import logging
import time
import json
from datetime import datetime
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


class GroqHealthMonitor:
    
    def __init__(self, api_key: str, model_id: str = "mixtral-8x7b-32768"):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = "https://api.groq.com/openai/v1"
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency": 0,
            "last_check": None,
            "last_error": None,
            "status": "unknown"
        }
        self.latencies = []  # Keep last 10 latencies
        self.max_latency_samples = 10
    
    def check_connectivity(self) -> Dict:
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            url = f"{self.base_url}/chat/completions"
            
            # Simple test prompt
            payload = {
                "model": self.model_id,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10,
                "temperature": 0.1,
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            latency = time.time() - start_time
            self.latencies.append(latency)
            if len(self.latencies) > self.max_latency_samples:
                self.latencies.pop(0)
            
            self.stats["total_requests"] += 1
            
            if response.status_code == 200:
                self.stats["successful_requests"] += 1
                self.stats["status"] = "healthy"
                self.stats["last_error"] = None
                self.stats["avg_latency"] = sum(self.latencies) / len(self.latencies)
                logger.info(f"Groq API healthy (latency: {latency:.2f}s)")
                return {
                    "status": "healthy",
                    "latency": latency,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif response.status_code == 401:
                self.stats["status"] = "auth_failed"
                error_msg = "Invalid or expired Groq API key"
                self.stats["last_error"] = error_msg
                self.stats["failed_requests"] += 1
                logger.error(f"❌ {error_msg}")
                return {
                    "status": "auth_failed",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            
            elif response.status_code == 429:
                self.stats["status"] = "rate_limited"
                error_msg = "Groq API rate limit exceeded"
                self.stats["last_error"] = error_msg
                self.stats["failed_requests"] += 1
                logger.warning(f"⏳ {error_msg}")
                return {
                    "status": "rate_limited",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            
            else:
                self.stats["status"] = "error"
                error_msg = f"Groq API error: {response.status_code}"
                self.stats["last_error"] = error_msg
                self.stats["failed_requests"] += 1
                logger.error(f"❌ {error_msg}")
                return {
                    "status": "error",
                    "code": response.status_code,
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
        
        except requests.exceptions.Timeout:
            self.stats["status"] = "timeout"
            error_msg = "Groq API timeout (slow/overloaded)"
            self.stats["last_error"] = error_msg
            self.stats["failed_requests"] += 1
            logger.warning(f"⏱️ {error_msg}")
            return {
                "status": "timeout",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
        
        except requests.exceptions.ConnectionError:
            self.stats["status"] = "no_connection"
            error_msg = "Cannot reach Groq API (no internet or API down)"
            self.stats["last_error"] = error_msg
            self.stats["failed_requests"] += 1
            logger.error(f"🔌 {error_msg}")
            return {
                "status": "no_connection",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.stats["status"] = "unknown_error"
            self.stats["last_error"] = str(e)
            self.stats["failed_requests"] += 1
            logger.exception(f"❓ Unexpected error checking Groq: {e}")
            return {
                "status": "unknown_error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        finally:
            self.stats["last_check"] = datetime.now().isoformat()
    
    def get_status(self) -> Dict:
        """Get current health status."""
        return {
            **self.stats,
            "model": self.model_id,
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            )
        }
    
    def get_metrics_json(self) -> str:
        return json.dumps(self.get_status(), indent=2, default=str)


# Global monitor instance (lazy-loaded in Django)
_monitor: Optional[GroqHealthMonitor] = None


def get_health_monitor() -> Optional[GroqHealthMonitor]:
    global _monitor
    
    if _monitor is None:
        import os
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
            _monitor = GroqHealthMonitor(api_key, model)
    
    return _monitor
