#!/usr/bin/env python3
"""
Master Test Runner for SCALE System v2.0
Executes all comprehensive test suites and generates unified reports
"""

import sys
import os
import time
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

sys.path.insert(0, os.path.abspath('.'))

class TestSuiteResult:
    """Test suite execution result"""
    
    def __init__(self, name: str, success: bool, duration: float, details: str = ""):
        self.name = name
        self.success = success
        self.duration = duration
        self.details = details
        self.timestamp = datetime.now()

class MasterTestRunner:
    """Master test runner for all SCALE system test suites"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.test_results: List[TestSuiteResult] = []
        self.system_info = self.collect_system_info()
        
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for test report"""
        try:
            import platform
            import psutil
            
            return {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total // (1024 * 1024),  # MB
                'disk_free': psutil.disk_usage('.').free // (1024 * 1024 * 1024),  # GB
                'hostname': platform.node(),
                'architecture': platform.architecture()[0]
            }
        except Exception:
            return {
                'platform': 'Unknown',
                'python_version': sys.version.split()[0],
                'cpu_count': 'Unknown',
                'memory_total': 'Unknown',
                'disk_free': 'Unknown',
                'hostname': 'Unknown',
                'architecture': 'Unknown'
            }
    
    def run_master_test_suite(self) -> bool:
        """Execute all test suites in the SCALE system"""
        
        self.print_header()
        
        # Define test suites to run
        test_suites = [
            {
                'name': 'Authentication & Security Tests',
                'description': 'Authentication system, session management, and security validation',
                'script': 'tests/headless_auth_test.py',
                'timeout': 120,
                'critical': True
            },
            {
                'name': 'Master Data Management Tests',
                'description': 'CRUD operations for Products, Customers, Suppliers, and Transporters',
                'script': 'test_master_data_headless.py',
                'timeout': 90,
                'critical': True
            },
            {
                'name': 'Comprehensive E2E Tests',
                'description': 'End-to-end system functionality testing',
                'script': 'tests/comprehensive_e2e_test.py',
                'timeout': 300,
                'critical': True
            },
            {
                'name': 'Performance & Stress Tests',
                'description': 'System performance, scalability, and stress testing',
                'script': 'tests/performance_stress_test.py',
                'timeout': 600,
                'critical': False
            },
            {
                'name': 'UI Integration Tests',
                'description': 'User interface components and integration testing',
                'script': 'tests/ui_integration_test.py',
                'timeout': 180,
                'critical': True
            },
            {
                'name': 'Weight Simulation Tests',
                'description': 'Weight simulation and hardware integration testing',
                'script': 'tests/simple_headless_test.py',
                'timeout': 60,
                'critical': False
            }
        ]
        
        # Execute test suites
        critical_failures = 0
        total_failures = 0
        
        for suite_config in test_suites:
            print(f"\n{'=' * 80}")
            print(f"   {suite_config['name'].upper()}")
            print(f"{'=' * 80}")
            print(f"📄 Description: {suite_config['description']}")
            print(f"📁 Script: {suite_config['script']}")
            print(f"⏱️ Timeout: {suite_config['timeout']} seconds")
            print(f"⚠️ Critical: {'Yes' if suite_config['critical'] else 'No'}")
            print()
            
            # Execute the test suite
            result = self.execute_test_suite(suite_config)
            self.test_results.append(result)
            
            if not result.success:
                total_failures += 1
                if suite_config['critical']:
                    critical_failures += 1
            
            # Print immediate result
            status_emoji = "✅" if result.success else "❌"
            print(f"\n{status_emoji} {suite_config['name']}: {'PASSED' if result.success else 'FAILED'}")
            print(f"⏱️ Duration: {result.duration:.1f} seconds")
            if result.details:
                print(f"📝 Details: {result.details}")
        
        # Generate comprehensive report
        return self.generate_master_report(critical_failures, total_failures)
    
    def execute_test_suite(self, suite_config: Dict[str, Any]) -> TestSuiteResult:
        """Execute a single test suite"""
        
        script_path = suite_config['script']
        timeout = suite_config['timeout']
        suite_name = suite_config['name']
        
        start_time = time.time()
        
        # Check if script exists
        if not os.path.exists(script_path):
            return TestSuiteResult(
                name=suite_name,
                success=False,
                duration=0,
                details=f"Test script not found: {script_path}"
            )
        
        try:
            print(f"🚀 Executing: {script_path}")
            
            # Execute the test script
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()  # Clean up
                return TestSuiteResult(
                    name=suite_name,
                    success=False,
                    duration=time.time() - start_time,
                    details=f"Test suite timed out after {timeout} seconds"
                )
            
            duration = time.time() - start_time
            
            # Analyze results
            if return_code == 0:
                # Success
                success_details = self.extract_success_details(stdout)
                return TestSuiteResult(
                    name=suite_name,
                    success=True,
                    duration=duration,
                    details=success_details
                )
            else:
                # Failure
                failure_details = self.extract_failure_details(stdout, stderr)
                return TestSuiteResult(
                    name=suite_name,
                    success=False,
                    duration=duration,
                    details=failure_details
                )
                
        except Exception as e:
            return TestSuiteResult(
                name=suite_name,
                success=False,
                duration=time.time() - start_time,
                details=f"Execution error: {str(e)}"
            )
    
    def extract_success_details(self, output: str) -> str:
        """Extract success details from test output"""
        lines = output.split('\n')
        
        # Look for summary lines
        success_indicators = [
            'tests passed',
            'ALL TESTS PASSED',
            'SUCCESS',
            'EXCELLENT',
            'READY FOR PRODUCTION'
        ]
        
        for line in lines:
            for indicator in success_indicators:
                if indicator in line.upper():
                    return line.strip()
        
        # Look for percentage indicators
        for line in lines:
            if '%' in line and any(word in line.upper() for word in ['SUCCESS', 'PASS', 'COMPLETE']):
                return line.strip()
        
        return "Test suite completed successfully"
    
    def extract_failure_details(self, stdout: str, stderr: str) -> str:
        """Extract failure details from test output"""
        # Check stderr first
        if stderr.strip():
            stderr_lines = stderr.split('\n')
            for line in stderr_lines:
                if line.strip() and not line.startswith('The command'):
                    return f"Error: {line.strip()}"
        
        # Check stdout for failure indicators
        stdout_lines = stdout.split('\n')
        failure_indicators = [
            'FAILED',
            'ERROR',
            'CRITICAL',
            'test failed',
            'failures',
            'crashed'
        ]
        
        for line in stdout_lines:
            for indicator in failure_indicators:
                if indicator in line.upper():
                    return line.strip()
        
        return "Test suite failed (see logs for details)"
    
    def print_header(self):
        """Print master test runner header"""
        print("\n" + "=" * 100)
        print("   SCALE SYSTEM v2.0 - MASTER TEST RUNNER")
        print("   Comprehensive Testing Suite for Professional Weighbridge Management")
        print("=" * 100)
        
        print(f"🚀 Test Session Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖼️ Working Directory: {os.getcwd()}")
        
        print(f"\n🖥️ SYSTEM INFORMATION:")
        print(f"   Platform: {self.system_info['platform']}")
        print(f"   Python Version: {self.system_info['python_version']}")
        print(f"   CPU Cores: {self.system_info['cpu_count']}")
        print(f"   Memory: {self.system_info['memory_total']} MB")
        print(f"   Disk Space: {self.system_info['disk_free']} GB")
        print(f"   Hostname: {self.system_info['hostname']}")
        print(f"   Architecture: {self.system_info['architecture']}")
        
        print(f"\n🎯 TEST COVERAGE AREAS:")
        coverage_areas = [
            "• Authentication & User Management",
            "• Master Data CRUD Operations",
            "• Two-Pass Weighing Workflows",
            "• Hardware Integration & Communication",
            "• Transaction Management",
            "• Database Operations & Data Integrity",
            "• User Interface Components",
            "• Report Generation & Export",
            "• System Performance & Scalability",
            "• Error Handling & Edge Cases",
            "• Real-time Weight Monitoring",
            "• Configuration Management"
        ]
        
        for area in coverage_areas:
            print(f"   {area}")
        
        print(f"\n📋 TESTING APPROACH:")
        print(f"   • Headless automation for CI/CD compatibility")
        print(f"   • Mock hardware simulation for testing")
        print(f"   • Comprehensive error scenario coverage")
        print(f"   • Performance benchmarking and stress testing")
        print(f"   • Integration testing across all modules")
        print(f"   • Data validation and security testing")
    
    def generate_master_report(self, critical_failures: int, total_failures: int) -> bool:
        """Generate comprehensive master test report"""
        
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "=" * 100)
        print("   SCALE SYSTEM v2.0 - MASTER TEST REPORT")
        print("=" * 100)
        
        # Executive Summary
        print(f"📊 EXECUTIVE SUMMARY")
        print(f"   Test Session Duration: {total_duration / 60:.1f} minutes")
        print(f"   Total Test Suites: {len(self.test_results)}")
        print(f"   Successful Suites: {len(self.test_results) - total_failures}")
        print(f"   Failed Suites: {total_failures}")
        print(f"   Critical Failures: {critical_failures}")
        
        success_rate = ((len(self.test_results) - total_failures) / len(self.test_results)) * 100 if self.test_results else 0
        print(f"   Overall Success Rate: {success_rate:.1f}%")
        
        # Detailed Results
        print(f"\n📋 DETAILED TEST RESULTS")
        print(f"{'Test Suite':<40} {'Status':<10} {'Duration':<12} {'Details'}")
        print("-" * 120)
        
        for result in self.test_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            duration = f"{result.duration:.1f}s"
            details = result.details[:50] + "..." if len(result.details) > 50 else result.details
            print(f"{result.name:<40} {status:<10} {duration:<12} {details}")
        
        # Performance Analysis
        print(f"\n⚡ PERFORMANCE ANALYSIS")
        if self.test_results:
            total_test_time = sum(r.duration for r in self.test_results)
            avg_duration = total_test_time / len(self.test_results)
            slowest_test = max(self.test_results, key=lambda r: r.duration)
            fastest_test = min(self.test_results, key=lambda r: r.duration)
            
            print(f"   Total Testing Time: {total_test_time / 60:.1f} minutes")
            print(f"   Average Suite Duration: {avg_duration:.1f} seconds")
            print(f"   Slowest Test Suite: {slowest_test.name} ({slowest_test.duration:.1f}s)")
            print(f"   Fastest Test Suite: {fastest_test.name} ({fastest_test.duration:.1f}s)")
            
            # Performance benchmarks
            performance_issues = []
            for result in self.test_results:
                if result.duration > 300:  # 5 minutes
                    performance_issues.append(f"{result.name} took {result.duration:.1f}s")
            
            if performance_issues:
                print(f"   ⚠️ Performance Concerns:")
                for issue in performance_issues:
                    print(f"     • {issue}")
            else:
                print(f"   ✅ All test suites completed within acceptable time limits")
        
        # Quality Assessment
        print(f"\n🎯 QUALITY ASSESSMENT")
        
        # Test coverage analysis
        coverage_areas = {
            'Authentication': any('auth' in r.name.lower() for r in self.test_results),
            'Master Data': any('master data' in r.name.lower() for r in self.test_results),
            'End-to-End': any('e2e' in r.name.lower() for r in self.test_results),
            'Performance': any('performance' in r.name.lower() for r in self.test_results),
            'UI Integration': any('ui' in r.name.lower() for r in self.test_results),
            'Hardware': any('weight' in r.name.lower() or 'hardware' in r.name.lower() for r in self.test_results)
        }
        
        covered_areas = sum(1 for covered in coverage_areas.values() if covered)
        total_areas = len(coverage_areas)
        
        print(f"   Test Coverage: {covered_areas}/{total_areas} core areas ({(covered_areas/total_areas)*100:.1f}%)")
        
        for area, covered in coverage_areas.items():
            status = "✅" if covered else "❌"
            print(f"     {status} {area}")
        
        # Risk Assessment
        print(f"\n🚨 RISK ASSESSMENT")
        
        risk_level = "LOW"
        risk_color = "🟢"  # Green
        risk_recommendations = []
        
        if critical_failures > 0:
            risk_level = "HIGH"
            risk_color = "🔴"  # Red
            risk_recommendations.append(f"Resolve {critical_failures} critical test failures before deployment")
        
        if total_failures > len(self.test_results) * 0.3:  # More than 30% failures
            if risk_level != "HIGH":
                risk_level = "MEDIUM"
                risk_color = "🟡"  # Yellow
            risk_recommendations.append("High failure rate detected - thorough review recommended")
        
        if success_rate < 70:
            risk_level = "HIGH"
            risk_color = "🔴"  # Red
            risk_recommendations.append("Success rate below acceptable threshold (70%)")
        
        print(f"   {risk_color} Overall Risk Level: {risk_level}")
        
        if risk_recommendations:
            print(f"   📝 Risk Recommendations:")
            for rec in risk_recommendations:
                print(f"     • {rec}")
        else:
            print(f"   ✅ No major risks identified")
        
        # Deployment Readiness
        print(f"\n🚀 DEPLOYMENT READINESS")
        
        deployment_ready = True
        deployment_blockers = []
        
        if critical_failures > 0:
            deployment_ready = False
            deployment_blockers.append(f"{critical_failures} critical test failures")
        
        if success_rate < 80:
            deployment_ready = False
            deployment_blockers.append(f"Success rate {success_rate:.1f}% below 80% threshold")
        
        if covered_areas < total_areas * 0.8:  # Less than 80% coverage
            deployment_ready = False
            deployment_blockers.append(f"Insufficient test coverage ({(covered_areas/total_areas)*100:.1f}%)")
        
        if deployment_ready:
            print(f"   ✅ SYSTEM READY FOR DEPLOYMENT")
            print(f"   🎉 All critical tests passed")
            print(f"   💯 Quality metrics meet deployment standards")
            print(f"   🚀 Recommended: Proceed with production deployment")
        else:
            print(f"   ❌ SYSTEM NOT READY FOR DEPLOYMENT")
            print(f"   🚨 Deployment Blockers:")
            for blocker in deployment_blockers:
                print(f"     • {blocker}")
            print(f"   🔧 Recommended: Address issues before deployment")
        
        # Recommendations
        print(f"\n📝 RECOMMENDATIONS")
        
        if deployment_ready:
            print(f"   ✅ System Quality: EXCELLENT - Ready for production")
            print(f"   📋 Maintenance: Set up automated testing pipeline")
            print(f"   📈 Monitoring: Implement production monitoring")
            print(f"   🔄 Updates: Establish regular testing schedule")
        elif risk_level == "MEDIUM":
            print(f"   ⚠️ System Quality: GOOD - Minor fixes needed")
            print(f"   🔧 Priority: Address failed test suites")
            print(f"   📋 Testing: Re-run tests after fixes")
            print(f"   ⏳ Timeline: 1-2 days for resolution")
        else:
            print(f"   ❌ System Quality: NEEDS IMPROVEMENT")
            print(f"   🚨 Priority: Address critical failures immediately")
            print(f"   🔍 Investigation: Review failed test details")
            print(f"   🛠️ Development: Implement fixes and re-test")
            print(f"   ⏳ Timeline: 3-7 days for resolution")
        
        # Test Data and Artifacts
        print(f"\n📁 TEST ARTIFACTS")
        
        # Save detailed results to JSON
        results_json = {
            'session_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': total_duration,
                'system_info': self.system_info
            },
            'summary': {
                'total_suites': len(self.test_results),
                'successful_suites': len(self.test_results) - total_failures,
                'failed_suites': total_failures,
                'critical_failures': critical_failures,
                'success_rate': success_rate,
                'deployment_ready': deployment_ready,
                'risk_level': risk_level
            },
            'detailed_results': [
                {
                    'name': r.name,
                    'success': r.success,
                    'duration': r.duration,
                    'details': r.details,
                    'timestamp': r.timestamp.isoformat()
                } for r in self.test_results
            ]
        }
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f"test_results_{timestamp}.json"
        report_filename = f"test_report_{timestamp}.md"
        
        try:
            # Save JSON results
            with open(json_filename, 'w') as f:
                json.dump(results_json, f, indent=2, default=str)
            print(f"   📊 Detailed Results: {json_filename}")
            
            # Save markdown report
            self.save_markdown_report(report_filename, results_json)
            print(f"   📄 Test Report: {report_filename}")
            
            print(f"   📁 Log Files: Check individual test suite outputs")
            
        except Exception as e:
            print(f"   ⚠️ Could not save test artifacts: {e}")
        
        # Final Summary
        print(f"\n🏁 TESTING SESSION COMPLETED")
        print(f"   Duration: {total_duration / 60:.1f} minutes")
        print(f"   Result: {'SUCCESS' if deployment_ready else 'NEEDS ATTENTION'}")
        print(f"   Next Steps: {'Deploy to production' if deployment_ready else 'Fix issues and re-test'}")
        print("=" * 100)
        
        return deployment_ready
    
    def save_markdown_report(self, filename: str, results_json: Dict):
        """Save test report in markdown format"""
        
        with open(filename, 'w') as f:
            f.write("# SCALE System v2.0 - Test Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary
            f.write("## Executive Summary\n\n")
            summary = results_json['summary']
            f.write(f"- **Test Suites Executed**: {summary['total_suites']}\n")
            f.write(f"- **Success Rate**: {summary['success_rate']:.1f}%\n")
            f.write(f"- **Critical Failures**: {summary['critical_failures']}\n")
            f.write(f"- **Deployment Ready**: {'Yes' if summary['deployment_ready'] else 'No'}\n")
            f.write(f"- **Risk Level**: {summary['risk_level']}\n\n")
            
            # System Info
            f.write("## System Information\n\n")
            sys_info = results_json['session_info']['system_info']
            f.write(f"- **Platform**: {sys_info['platform']}\n")
            f.write(f"- **Python Version**: {sys_info['python_version']}\n")
            f.write(f"- **CPU Cores**: {sys_info['cpu_count']}\n")
            f.write(f"- **Memory**: {sys_info['memory_total']} MB\n")
            f.write(f"- **Architecture**: {sys_info['architecture']}\n\n")
            
            # Detailed Results
            f.write("## Test Suite Results\n\n")
            f.write("| Test Suite | Status | Duration | Details |\n")
            f.write("|------------|--------|----------|---------|\n")
            
            for result in results_json['detailed_results']:
                status = "✅ PASS" if result['success'] else "❌ FAIL"
                duration = f"{result['duration']:.1f}s"
                details = result['details'][:50] + "..." if len(result['details']) > 50 else result['details']
                f.write(f"| {result['name']} | {status} | {duration} | {details} |\n")
            
            f.write("\n## Recommendations\n\n")
            if summary['deployment_ready']:
                f.write("✅ **System is ready for production deployment**\n\n")
                f.write("- All critical tests passed\n")
                f.write("- Quality metrics meet standards\n")
                f.write("- Recommended to proceed with deployment\n")
            else:
                f.write("⚠️ **System needs attention before deployment**\n\n")
                f.write("- Address failed test suites\n")
                f.write("- Re-run tests after fixes\n")
                f.write("- Review detailed test outputs\n")

def main():
    """Main execution function"""
    
    # Change to scale_system directory
    if not os.path.exists('tests') and not os.path.exists('database'):
        scale_system_dir = 'scale_system'
        if os.path.exists(scale_system_dir):
            os.chdir(scale_system_dir)
            print(f"Changed to directory: {os.getcwd()}")
        else:
            print("Error: Cannot find scale_system directory")
            return 1
    
    # Initialize master test runner
    master_runner = MasterTestRunner()
    
    try:
        # Execute all test suites
        success = master_runner.run_master_test_suite()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Master test suite interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: Master test runner crashed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
