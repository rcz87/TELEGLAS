"""
TELEGLAS GPT API - Staging Test Runner
Automated staging environment testing and reporting
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
import pytest


class StagingTestRunner:
    """Automated staging test runner with comprehensive reporting"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent.parent
        self.results = {
            "test_run": {
                "timestamp": datetime.utcnow().isoformat(),
                "environment": "staging",
                "python_version": sys.version,
                "test_results": {},
                "summary": {}
            }
        }
    
    def setup_staging_environment(self):
        """Setup staging environment variables"""
        staging_env = {
            "GPT_API_HOST": "127.0.0.1",
            "GPT_API_PORT": "8001",
            "GPT_API_DEBUG": "true",
            "GPT_API_API_KEYS": "staging-key-1,staging-key-2,staging-test-key",
            "GPT_API_REQUIRE_AUTH": "true",
            "GPT_API_IP_ALLOWLIST": "127.0.0.1,::1",
            "GPT_API_RATE_LIMIT_REQUESTS": "50",
            "GPT_API_RATE_LIMIT_WINDOW": "60",
            "GPT_API_CACHE_ENABLED": "true",
            "GPT_API_CACHE_TTL": "60",
            "GPT_API_REDIS_URL": "redis://localhost:6379/1",
            "GPT_API_ANALYTICS_ENABLED": "true",
            "GPT_API_WEBHOOKS_ENABLED": "false",
        }
        
        # Set environment variables
        for key, value in staging_env.items():
            os.environ[key] = value
        
        print("✅ Staging environment configured")
        return staging_env
    
    def run_test_suite(self, test_name, test_file):
        """Run specific test suite and collect results"""
        print(f"\n🧪 Running {test_name}...")
        
        start_time = time.time()
        
        # Run pytest with JSON output
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-v",
            "--tb=short",
            "--maxfail=5",
            "--json-report",
            "--json-report-file=/tmp/test_results.json"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            try:
                with open("/tmp/test_results.json", "r") as f:
                    test_results = json.load(f)
            except:
                test_results = self.parse_pytest_output(result.stdout)
            
            self.results["test_results"][test_name] = {
                "duration_seconds": round(duration, 2),
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_results": test_results,
                "status": "PASSED" if result.returncode == 0 else "FAILED"
            }
            
            status = "✅ PASSED" if result.returncode == 0 else "❌ FAILED"
            print(f"{status} {test_name} ({duration:.2f}s)")
            
            if result.returncode != 0:
                print(f"❌ Error output:\n{result.stderr}")
            
        except Exception as e:
            print(f"❌ Error running {test_name}: {e}")
            self.results["test_results"][test_name] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    def parse_pytest_output(self, output):
        """Parse pytest output when JSON report is not available"""
        lines = output.split('\n')
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0
        }
        
        for line in lines:
            if "=" in line and "passed" in line:
                # Parse summary line like "=== 5 passed, 2 failed in 10.5s ==="
                parts = line.split("=")[1].strip().split(" in ")[0].split(", ")
                for part in parts:
                    if "passed" in part:
                        results["passed"] = int(part.split()[0])
                    elif "failed" in part:
                        results["failed"] = int(part.split()[0])
                    elif "error" in part:
                        results["errors"] = int(part.split()[0])
                    elif "skipped" in part:
                        results["skipped"] = int(part.split()[0])
                
                results["total"] = results["passed"] + results["failed"] + results["errors"] + results["skipped"]
                break
        
        return results
    
    def run_all_tests(self):
        """Run all staging test suites"""
        print("🚀 Starting TELEGLAS GPT API Staging Tests")
        print("=" * 50)
        
        # Setup environment
        self.setup_staging_environment()
        
        # Define test suites
        test_suites = [
            ("Environment Setup", self.test_dir / "test_staging_integration.py::TestStagingEnvironment"),
            ("Schema Validation", self.test_dir / "test_staging_integration.py::TestEndpointSchemaValidation"),
            ("Authentication", self.test_dir / "test_staging_integration.py::TestAuthenticationAndAuthorization"),
            ("Core Service Integration", self.test_dir / "test_staging_integration.py::TestCoreServiceIntegration"),
            ("Caching Integration", self.test_dir / "test_staging_integration.py::TestCachingIntegration"),
            ("Concurrency & Error Handling", self.test_dir / "test_staging_integration.py::TestConcurrencyAndErrorHandling"),
            ("Analytics & Monitoring", self.test_dir / "test_staging_integration.py::TestAnalyticsAndMonitoring"),
            ("Edge Cases", self.test_dir / "test_staging_integration.py::TestEdgeCasesAndBoundaryConditions"),
        ]
        
        # Run each test suite
        for test_name, test_file in test_suites:
            self.run_test_suite(test_name, test_file)
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        # Print final report
        self.print_final_report()
    
    def generate_summary(self):
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        
        for test_name, results in self.results["test_results"].items():
            status = results.get("status", "ERROR")
            
            if status == "PASSED":
                passed_tests += 1
            elif status == "FAILED":
                failed_tests += 1
            else:
                error_tests += 1
            
            total_tests += 1
        
        self.results["test_run"]["summary"] = {
            "total_test_suites": total_tests,
            "passed_suites": passed_tests,
            "failed_suites": failed_tests,
            "error_suites": error_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
            "overall_status": "PASSED" if failed_tests == 0 and error_tests == 0 else "FAILED"
        }
    
    def save_results(self):
        """Save test results to file"""
        results_dir = self.project_root / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"staging_test_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📄 Test results saved to: {results_file}")
        return results_file
    
    def print_final_report(self):
        """Print final test report"""
        summary = self.results["test_run"]["summary"]
        
        print("\n" + "=" * 50)
        print("📊 STAGING TEST SUMMARY")
        print("=" * 50)
        print(f"Total Test Suites: {summary['total_test_suites']}")
        print(f"Passed: {summary['passed_suites']} ✅")
        print(f"Failed: {summary['failed_suites']} ❌")
        print(f"Errors: {summary['error_suites']} ⚠️")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Overall Status: {summary['overall_status']}")
        
        if summary["overall_status"] == "PASSED":
            print("\n🎉 ALL TESTS PASSED - READY FOR PRODUCTION DEPLOYMENT")
        else:
            print("\n⚠️ SOME TESTS FAILED - REVIEW BEFORE PRODUCTION DEPLOYMENT")
            print("\nFailed test suites:")
            for test_name, results in self.results["test_results"].items():
                if results.get("status") in ["FAILED", "ERROR"]:
                    print(f"  ❌ {test_name}")
        
        print("\n" + "=" * 50)


class StagingEnvironmentValidator:
    """Validate staging environment before testing"""
    
    @staticmethod
    def validate_dependencies():
        """Validate required dependencies"""
        print("🔍 Validating dependencies...")
        
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "pytest",
            "redis",
            "aiohttp"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ {package}")
            except ImportError:
                print(f"❌ {package} - MISSING")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        print("✅ All dependencies satisfied")
        return True
    
    @staticmethod
    def validate_services():
        """Validate external services"""
        print("\n🔍 Validating external services...")
        
        # Check Redis connection
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
            r.ping()
            print("✅ Redis (DB 1) - Connected")
        except Exception as e:
            print(f"❌ Redis (DB 1) - Failed: {e}")
            return False
        
        print("✅ All external services available")
        return True
    
    @staticmethod
    def validate_codebase():
        """Validate codebase structure"""
        print("\n🔍 Validating codebase structure...")
        
        required_files = [
            "gpt_api/gpt_api_main.py",
            "gpt_api/config.py",
            "gpt_api/auth.py",
            "gpt_api/schemas.py",
            "gpt_api/cache.py",
            "gpt_api/analytics.py",
            "services/market_data_core.py"
        ]
        
        project_root = Path(__file__).parent.parent.parent
        missing_files = []
        
        for file_path in required_files:
            full_path = project_root / file_path
            if full_path.exists():
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path} - MISSING")
                missing_files.append(file_path)
        
        if missing_files:
            print(f"\n❌ Missing files: {', '.join(missing_files)}")
            return False
        
        print("✅ All required files present")
        return True


def main():
    """Main entry point"""
    print("🚀 TELEGLAS GPT API - Staging Test Runner")
    print("=" * 50)
    
    # Validate environment
    validator = StagingEnvironmentValidator()
    
    if not validator.validate_dependencies():
        print("❌ Dependency validation failed")
        return 1
    
    if not validator.validate_services():
        print("❌ Service validation failed")
        return 1
    
    if not validator.validate_codebase():
        print("❌ Codebase validation failed")
        return 1
    
    print("\n✅ Environment validation passed")
    
    # Run tests
    runner = StagingTestRunner()
    runner.run_all_tests()
    
    # Return exit code based on results
    summary = runner.results["test_run"]["summary"]
    return 0 if summary["overall_status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
