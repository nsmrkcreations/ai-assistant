#!/usr/bin/env python3
"""
Comprehensive test runner for AI Assistant Desktop Application
Runs all types of tests with proper reporting and coverage
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
import json
from typing import List, Dict, Any
import concurrent.futures
from dataclasses import dataclass

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    passed: bool
    duration: float
    output: str
    coverage: float = 0.0

class TestRunner:
    """Comprehensive test runner for the AI Assistant application"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backend_dir = self.root_dir / "backend"
        self.frontend_dir = self.root_dir / "frontend"
        self.results: List[TestResult] = []
        
    def run_all_tests(self, test_types: List[str] = None, parallel: bool = False) -> bool:
        """Run all specified test types"""
        if test_types is None:
            test_types = [
                "unit", "integration", "performance", 
                "security", "edge_case", "frontend"
            ]
        
        print("🚀 Starting AI Assistant Test Suite")
        print(f"📁 Root directory: {self.root_dir}")
        print(f"🧪 Test types: {', '.join(test_types)}")
        print("=" * 60)
        
        start_time = time.time()
        
        if parallel and len(test_types) > 1:
            success = self._run_tests_parallel(test_types)
        else:
            success = self._run_tests_sequential(test_types)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        self._print_summary(total_duration)
        
        return success
    
    def _run_tests_sequential(self, test_types: List[str]) -> bool:
        """Run tests sequentially"""
        all_passed = True
        
        for test_type in test_types:
            if test_type == "frontend":
                result = self._run_frontend_tests()
            else:
                result = self._run_backend_tests(test_type)
            
            self.results.append(result)
            
            if not result.passed:
                all_passed = False
                if test_type in ["unit", "integration"]:
                    print(f"❌ Critical test failure in {test_type}, stopping execution")
                    break
        
        return all_passed
    
    def _run_tests_parallel(self, test_types: List[str]) -> bool:
        """Run tests in parallel where possible"""
        # Separate frontend and backend tests
        backend_tests = [t for t in test_types if t != "frontend"]
        frontend_tests = ["frontend"] if "frontend" in test_types else []
        
        all_passed = True
        
        # Run backend tests in parallel
        if backend_tests:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_test = {
                    executor.submit(self._run_backend_tests, test_type): test_type 
                    for test_type in backend_tests
                }
                
                for future in concurrent.futures.as_completed(future_to_test):
                    test_type = future_to_test[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                        if not result.passed:
                            all_passed = False
                    except Exception as e:
                        print(f"❌ Test {test_type} failed with exception: {e}")
                        all_passed = False
        
        # Run frontend tests separately (they may conflict with backend)
        if frontend_tests:
            result = self._run_frontend_tests()
            self.results.append(result)
            if not result.passed:
                all_passed = False
        
        return all_passed
    
    def _run_backend_tests(self, test_type: str) -> TestResult:
        """Run backend tests of specified type"""
        print(f"\n🧪 Running {test_type} tests...")
        
        start_time = time.time()
        
        # Prepare pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "-v",
            f"-m", test_type,
            "--tb=short",
            "--durations=10"
        ]
        
        # Add coverage for unit and integration tests
        if test_type in ["unit", "integration"]:
            cmd.extend([
                "--cov=services",
                "--cov=models", 
                "--cov=utils",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ])
        
        # Add specific test files based on type
        if test_type == "unit":
            cmd.extend([
                "tests/test_llm_service.py",
                "tests/test_automation_service.py",
                "tests/test_security_service.py"
            ])
        elif test_type == "integration":
            cmd.append("tests/test_integration.py")
        elif test_type == "performance":
            cmd.append("tests/test_performance.py")
        elif test_type == "edge_case":
            cmd.append("tests/test_edge_cases.py")
        
        # Run tests
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Check for coverage data
            coverage = 0.0
            coverage_file = self.backend_dir / "coverage.json"
            if coverage_file.exists():
                try:
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                        coverage = coverage_data.get("totals", {}).get("percent_covered", 0.0)
                except:
                    pass
            
            success = result.returncode == 0
            
            if success:
                print(f"✅ {test_type} tests passed ({duration:.2f}s)")
                if coverage > 0:
                    print(f"📊 Coverage: {coverage:.1f}%")
            else:
                print(f"❌ {test_type} tests failed ({duration:.2f}s)")
                print("Error output:")
                print(result.stderr)
            
            return TestResult(
                name=f"backend_{test_type}",
                passed=success,
                duration=duration,
                output=result.stdout + result.stderr,
                coverage=coverage
            )
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_type} tests timed out")
            return TestResult(
                name=f"backend_{test_type}",
                passed=False,
                duration=600,
                output="Test timed out after 10 minutes"
            )
        except Exception as e:
            print(f"❌ {test_type} tests failed with exception: {e}")
            return TestResult(
                name=f"backend_{test_type}",
                passed=False,
                duration=0,
                output=str(e)
            )
    
    def _run_frontend_tests(self) -> TestResult:
        """Run frontend tests"""
        print(f"\n🧪 Running frontend tests...")
        
        start_time = time.time()
        
        # Check if node_modules exists
        if not (self.frontend_dir / "node_modules").exists():
            print("📦 Installing frontend dependencies...")
            npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
            npm_install = subprocess.run(
                [npm_cmd, "install"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            if npm_install.returncode != 0:
                print("❌ Failed to install frontend dependencies")
                return TestResult(
                    name="frontend",
                    passed=False,
                    duration=0,
                    output="Failed to install dependencies"
                )
        
        # Run Jest tests
        npm_cmd = "npm.cmd" if os.name == 'nt' else "npm"
        cmd = [npm_cmd, "test", "--", "--coverage", "--watchAll=false", "--verbose"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            if success:
                print(f"✅ Frontend tests passed ({duration:.2f}s)")
            else:
                print(f"❌ Frontend tests failed ({duration:.2f}s)")
                print("Error output:")
                print(result.stderr)
            
            return TestResult(
                name="frontend",
                passed=success,
                duration=duration,
                output=result.stdout + result.stderr
            )
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Frontend tests timed out")
            return TestResult(
                name="frontend",
                passed=False,
                duration=300,
                output="Frontend tests timed out after 5 minutes"
            )
        except Exception as e:
            print(f"❌ Frontend tests failed with exception: {e}")
            return TestResult(
                name="frontend",
                passed=False,
                duration=0,
                output=str(e)
            )
    
    def _print_summary(self, total_duration: float):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]
        
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"⏱️  Total Duration: {total_duration:.2f}s")
        
        if self.results:
            avg_coverage = sum(r.coverage for r in self.results if r.coverage > 0) / len([r for r in self.results if r.coverage > 0])
            if avg_coverage > 0:
                print(f"📊 Average Coverage: {avg_coverage:.1f}%")
        
        print("\nDetailed Results:")
        for result in self.results:
            status = "✅" if result.passed else "❌"
            coverage_info = f" (Coverage: {result.coverage:.1f}%)" if result.coverage > 0 else ""
            print(f"  {status} {result.name}: {result.duration:.2f}s{coverage_info}")
        
        if failed_tests:
            print(f"\n❌ {len(failed_tests)} test(s) failed:")
            for result in failed_tests:
                print(f"  - {result.name}")
        
        print("\n" + "=" * 60)
        
        if len(failed_tests) == 0:
            print("🎉 All tests passed! Ready for production.")
        else:
            print("🔧 Some tests failed. Please review and fix issues.")
    
    def run_specific_test(self, test_file: str, test_name: str = None) -> bool:
        """Run a specific test file or test function"""
        print(f"🧪 Running specific test: {test_file}")
        
        if test_name:
            print(f"   Function: {test_name}")
        
        cmd = [sys.executable, "-m", "pytest", "-v", test_file]
        
        if test_name:
            cmd.extend(["-k", test_name])
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                timeout=300
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out")
            return False
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            return False
    
    def run_load_test(self, duration: int = 60, users: int = 10) -> bool:
        """Run load tests using locust"""
        print(f"🚀 Running load test ({users} users, {duration}s)")
        
        # Create a simple locust file for testing
        locust_file = self.backend_dir / "locustfile.py"
        locust_content = f'''
from locust import HttpUser, task, between
import json

class AIAssistantUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def send_message(self):
        self.client.post("/chat/message", json={{
            "message": "Hello AI Assistant",
            "include_audio": False
        }})
    
    @task(1)
    def check_status(self):
        self.client.get("/system/status")
    
    @task(1)
    def health_check(self):
        self.client.get("/health")
'''
        
        with open(locust_file, 'w') as f:
            f.write(locust_content)
        
        try:
            cmd = [
                "locust",
                "-f", str(locust_file),
                "--host", "http://localhost:8000",
                "--users", str(users),
                "--spawn-rate", "2",
                "--run-time", f"{duration}s",
                "--headless"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                timeout=duration + 30
            )
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print("⏰ Load test timed out")
            return False
        except Exception as e:
            print(f"❌ Load test failed: {e}")
            return False
        finally:
            # Cleanup
            if locust_file.exists():
                locust_file.unlink()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AI Assistant Test Runner")
    
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["unit", "integration", "performance", "security", "edge_case", "frontend", "all"],
        default=["all"],
        help="Test types to run"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--specific",
        help="Run specific test file"
    )
    
    parser.add_argument(
        "--function",
        help="Run specific test function (use with --specific)"
    )
    
    parser.add_argument(
        "--load-test",
        action="store_true",
        help="Run load tests"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Load test duration in seconds"
    )
    
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of concurrent users for load test"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.load_test:
        success = runner.run_load_test(args.duration, args.users)
    elif args.specific:
        success = runner.run_specific_test(args.specific, args.function)
    else:
        test_types = args.types
        if "all" in test_types:
            test_types = ["unit", "integration", "performance", "security", "edge_case", "frontend"]
        
        success = runner.run_all_tests(test_types, args.parallel)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()