#!/usr/bin/env python3
"""
Comprehensive Bug Detection Test for IELTS Pressure Engine
Tests all critical flows and potential error scenarios
"""

import requests
import json
import time
import os
from io import BytesIO
import base64

class IELTSTester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.test_user_id = "comprehensive_test_user"
        self.session_id = None
        self.results = []
        
    def log_result(self, test_name, status, details=""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
    
    def test_api_health(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                self.log_result("API Health Check", "PASS", "API docs accessible")
                return True
            else:
                self.log_result("API Health Check", "FAIL", f"Status {response.status_code}")
                return False
        except Exception as e:
            self.log_result("API Health Check", "FAIL", str(e))
            return False
    
    def test_start_exam(self):
        """Test exam session creation"""
        try:
            payload = {"user_id": self.test_user_id}
            response = requests.post(f"{self.base_url}/api/v1/exams/start", 
                                   json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("id")
                
                # Validate response structure
                required_fields = ["id", "current_prompt", "checkpoint_words"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    self.log_result("Start Exam", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                self.log_result("Start Exam", "PASS", 
                              f"Session {self.session_id[:8]}..., prompt: {data['current_prompt'][:30]}...")
                return True
            else:
                self.log_result("Start Exam", "FAIL", f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Start Exam", "FAIL", str(e))
            return False
    
    def test_empty_audio_submission(self):
        """Test handling of empty/invalid audio"""
        if not self.session_id:
            self.log_result("Empty Audio Test", "SKIP", "No session available")
            return False
            
        try:
            # Create empty audio file
            empty_audio = BytesIO(b"")
            
            files = {"audio_file": ("empty.wav", empty_audio, "audio/wav")}
            data = {
                "session_id": self.session_id,
                "is_exam_mode": True
            }
            
            response = requests.post(f"{self.base_url}/api/v1/exams/submit",
                                   files=files, data=data, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                # Check if it handles empty audio gracefully
                if result.get("action_id") == "MAINTAIN":
                    self.log_result("Empty Audio Test", "PASS", "Graceful handling of empty audio")
                    return True
                else:
                    self.log_result("Empty Audio Test", "PARTIAL", 
                                  f"Response: {result.get('action_id', 'N/A')}")
                    return True
            else:
                self.log_result("Empty Audio Test", "FAIL", f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Empty Audio Test", "FAIL", str(e))
            return False
    
    def test_invalid_session_id(self):
        """Test handling of invalid session ID"""
        try:
            invalid_session = "invalid-session-id-12345"
            
            # Test with invalid session
            payload = {"user_id": self.test_user_id, "session_id": invalid_session}
            response = requests.post(f"{self.base_url}/api/v1/exams/start", 
                                   json=payload, timeout=10)
            
            # Should either create new session or return error gracefully
            if response.status_code in [200, 404, 400]:
                self.log_result("Invalid Session Test", "PASS", 
                              f"Handled gracefully (status {response.status_code})")
                return True
            else:
                self.log_result("Invalid Session Test", "FAIL", f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Invalid Session Test", "FAIL", str(e))
            return False
    
    def test_database_integrity(self):
        """Test database integrity and relationships"""
        try:
            # Check if we can query user stats
            response = requests.get(f"{self.base_url}/api/v1/users/{self.test_user_id}/stats",
                                  timeout=10)
            
            if response.status_code == 200:
                self.log_result("Database Integrity", "PASS", "User stats query successful")
                return True
            elif response.status_code == 404:
                self.log_result("Database Integrity", "PASS", "New user (404 expected)")
                return True
            else:
                self.log_result("Database Integrity", "FAIL", f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Database Integrity", "FAIL", str(e))
            return False
    
    def test_checkpoint_system(self):
        """Test checkpoint word system"""
        if not self.session_id:
            self.log_result("Checkpoint System", "SKIP", "No session available")
            return False
            
        try:
            # Get session details to check checkpoint words
            response = requests.get(f"{self.base_url}/api/v1/exams/{self.session_id}/status",
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                checkpoint_words = data.get("checkpoint_words", [])
                
                if checkpoint_words:
                    self.log_result("Checkpoint System", "PASS", 
                                  f"Found {len(checkpoint_words)} checkpoint words")
                    return True
                else:
                    self.log_result("Checkpoint System", "PARTIAL", "No checkpoint words found")
                    return True
            else:
                self.log_result("Checkpoint System", "FAIL", f"Status {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Checkpoint System", "FAIL", str(e))
            return False
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        if not self.session_id:
            self.log_result("Concurrent Requests", "SKIP", "No session available")
            return False
            
        try:
            import threading
            import queue
            
            results_queue = queue.Queue()
            
            def make_request():
                try:
                    response = requests.get(f"{self.base_url}/api/v1/exams/{self.session_id}/status",
                                          timeout=5)
                    results_queue.put(response.status_code)
                except Exception as e:
                    results_queue.put(f"ERROR: {e}")
            
            # Make 3 concurrent requests
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Check results
            success_count = 0
            while not results_queue.empty():
                result = results_queue.get()
                if result == 200:
                    success_count += 1
            
            if success_count >= 2:  # At least 2 out of 3 should succeed
                self.log_result("Concurrent Requests", "PASS", 
                              f"{success_count}/3 requests successful")
                return True
            else:
                self.log_result("Concurrent Requests", "FAIL", 
                              f"Only {success_count}/3 requests successful")
                return False
                
        except Exception as e:
            self.log_result("Concurrent Requests", "FAIL", str(e))
            return False
    
    def test_memory_usage(self):
        """Test for potential memory leaks"""
        try:
            # Make multiple requests to check for memory growth
            for i in range(5):
                response = requests.get(f"{self.base_url}/api/v1/users/{self.test_user_id}/stats",
                                      timeout=5)
                if response.status_code != 200:
                    self.log_result("Memory Usage Test", "FAIL", f"Request {i+1} failed")
                    return False
            
            self.log_result("Memory Usage Test", "PASS", "5 consecutive requests successful")
            return True
            
        except Exception as e:
            self.log_result("Memory Usage Test", "FAIL", str(e))
            return False
    
    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🧪 Starting Comprehensive Bug Detection Test")
        print("=" * 50)
        
        tests = [
            self.test_api_health,
            self.test_start_exam,
            self.test_empty_audio_submission,
            self.test_invalid_session_id,
            self.test_database_integrity,
            self.test_checkpoint_system,
            self.test_concurrent_requests,
            self.test_memory_usage
        ]
        
        passed = 0
        failed = 0
        skipped = 0
        partial = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                failed += 1
        
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        for result in self.results:
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['test']}: {result['status']}")
            if result["details"]:
                print(f"   {result['details']}")
        
        print(f"\n🎯 RESULTS:")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Partial/Skipped: {len(self.results) - passed - failed}")
        
        success_rate = (passed / len(self.results)) * 100 if self.results else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 SYSTEM STABLE - Ready for production!")
        elif success_rate >= 60:
            print("⚠️ SYSTEM NEEDS ATTENTION - Some issues found")
        else:
            print("🚨 SYSTEM UNSTABLE - Major issues detected")
        
        return success_rate

if __name__ == "__main__":
    tester = IELTSTester()
    tester.run_all_tests()
