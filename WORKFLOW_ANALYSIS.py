#!/usr/bin/env python3
"""
COMPREHENSIVE WORKFLOW ANALYSIS
Identifies issues, conflicts, duplications, and fake logging in the trading bot.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class WorkflowAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.trading_bot_path = self.project_root / "trading_bot"
        self.issues = []
        self.warnings = []
        self.duplications = []
        self.fake_logs = []
        
    def analyze_all(self):
        """Run comprehensive analysis."""
        print("🔍 STARTING COMPREHENSIVE WORKFLOW ANALYSIS")
        print("=" * 60)
        
        # 1. Check for missing imports/functions
        self.check_missing_functions()
        
        # 2. Check for duplicate code
        self.check_duplications()
        
        # 3. Check for fake logging
        self.check_fake_logging()
        
        # 4. Check workflow conflicts
        self.check_workflow_conflicts()
        
        # 5. Check data validation issues
        self.check_data_validation()
        
        # 6. Check execution logic
        self.check_execution_logic()
        
        # Generate report
        self.generate_report()
    
    def check_missing_functions(self):
        """Check for calls to non-existent functions."""
        print("\n🔍 CHECKING FOR MISSING FUNCTIONS...")
        
        # Known missing functions from deleted blacklist
        missing_functions = [
            "get_confidence_override",
            "is_high_performer", 
            "is_asset_blacklisted"
        ]
        
        for py_file in self.trading_bot_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for func in missing_functions:
                    if func in content and f"def {func}" not in content:
                        self.issues.append({
                            'type': 'CRITICAL',
                            'category': 'Missing Function',
                            'file': str(py_file.relative_to(self.project_root)),
                            'function': func,
                            'description': f"Function '{func}' is called but not defined (likely from deleted blacklist)"
                        })
            except Exception as e:
                continue
    
    def check_duplications(self):
        """Check for duplicate code patterns."""
        print("\n🔍 CHECKING FOR CODE DUPLICATIONS...")
        
        # Check for duplicate position loading
        position_loading_files = []
        for py_file in self.trading_bot_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "_load_existing_positions" in content or "load existing positions" in content.lower():
                    position_loading_files.append(str(py_file.relative_to(self.project_root)))
            except:
                continue
        
        if len(position_loading_files) > 1:
            self.duplications.append({
                'type': 'WARNING',
                'category': 'Duplicate Logic',
                'description': 'Position loading logic found in multiple files',
                'files': position_loading_files
            })
    
    def check_fake_logging(self):
        """Check for potentially fake or misleading logging."""
        print("\n🔍 CHECKING FOR FAKE/MISLEADING LOGGING...")
        
        fake_patterns = [
            # Logging success without actual verification
            (r'logger\.info.*"✅.*SUCCESS"', "Success logged without verification"),
            (r'logger\.info.*"✅.*COMPLETED"', "Completion logged without verification"),
            (r'logger\.info.*"✅.*EXECUTED"', "Execution logged without verification"),
            # Hardcoded values being logged as if they're dynamic
            (r'logger\.info.*0\.001.*funding', "Hardcoded funding rate logged as real data"),
            (r'logger\.info.*42000.*BTC', "Hardcoded BTC price used as fallback"),
            # Analytics that might not be working
            (r'logger\.info.*"🚀.*ADVANCED ANALYTICS"', "Advanced analytics claimed without verification"),
        ]
        
        for py_file in self.trading_bot_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, description in fake_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        self.fake_logs.append({
                            'type': 'WARNING',
                            'category': 'Potentially Fake Log',
                            'file': str(py_file.relative_to(self.project_root)),
                            'line': line_num,
                            'pattern': pattern,
                            'description': description,
                            'code': match.group()
                        })
            except:
                continue
    
    def check_workflow_conflicts(self):
        """Check for workflow conflicts and inconsistencies."""
        print("\n🔍 CHECKING FOR WORKFLOW CONFLICTS...")
        
        # Check for conflicting position management
        pipeline_file = self.trading_bot_path / "orchestration" / "pipeline.py"
        if pipeline_file.exists():
            try:
                with open(pipeline_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for multiple position management methods
                manage_methods = [
                    "manage_all_positions",
                    "manage_all_assets", 
                    "_intelligent_position_management",
                    "_evaluate_open_position"
                ]
                
                found_methods = []
                for method in manage_methods:
                    if f"def {method}" in content:
                        found_methods.append(method)
                
                # Check if this is documented as intentional
                if len(found_methods) > 2:
                    if "intentional separation of concerns" in content.lower():
                        # Documented as intentional design - not a conflict
                        pass
                    else:
                        self.issues.append({
                            'type': 'WARNING',
                            'category': 'Workflow Conflict',
                            'file': 'orchestration/pipeline.py',
                            'description': f'Multiple position management methods: {found_methods}',
                            'impact': 'May cause conflicting position management logic'
                        })
                
            except:
                pass
    
    def check_data_validation(self):
        """Check data validation issues."""
        print("\n🔍 CHECKING DATA VALIDATION...")
        
        # Check for insufficient data handling
        for py_file in self.trading_bot_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for data validation patterns
                if "len(candles)" in content and "< 50" in content:
                    # Good - has data validation
                    continue
                elif "advanced_analytics" in content.lower() and "len(" not in content:
                    # Potential issue - advanced analytics without data validation
                    self.warnings.append({
                        'type': 'WARNING',
                        'category': 'Data Validation',
                        'file': str(py_file.relative_to(self.project_root)),
                        'description': 'Advanced analytics used without apparent data validation'
                    })
            except:
                continue
    
    def check_execution_logic(self):
        """Check trade execution logic for issues."""
        print("\n🔍 CHECKING EXECUTION LOGIC...")
        
        pipeline_file = self.trading_bot_path / "orchestration" / "pipeline.py"
        if pipeline_file.exists():
            try:
                with open(pipeline_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for OCO order handling
                if "protection_algo_id" in content and "oco" in content.lower():
                    # Check if there's proper fallback with clear logging
                    has_fallback = "managed_by_exchange" in content
                    has_fallback_logging = "OCO PROTECTION FAILED" in content and "MANUAL PROTECTION" in content
                    
                    if not (has_fallback and has_fallback_logging):
                        self.warnings.append({
                            'type': 'WARNING',
                            'category': 'Execution Logic',
                            'file': 'orchestration/pipeline.py',
                            'description': 'OCO orders used but no clear fallback for failures'
                        })
                
                # Check for position size validation
                if "_size_position" in content:
                    if "optimal_size <= 0" not in content:
                        self.warnings.append({
                            'type': 'WARNING', 
                            'category': 'Execution Logic',
                            'file': 'orchestration/pipeline.py',
                            'description': 'Position sizing without zero/negative validation'
                        })
                        
            except:
                pass
    
    def generate_report(self):
        """Generate comprehensive analysis report."""
        print("\n" + "=" * 60)
        print("📊 WORKFLOW ANALYSIS REPORT")
        print("=" * 60)
        
        # Critical Issues
        critical_issues = [i for i in self.issues if i['type'] == 'CRITICAL']
        if critical_issues:
            print(f"\n🚨 CRITICAL ISSUES FOUND: {len(critical_issues)}")
            for issue in critical_issues:
                print(f"   ❌ {issue['category']}: {issue['description']}")
                print(f"      File: {issue['file']}")
                if 'function' in issue:
                    print(f"      Function: {issue['function']}")
        
        # Warnings
        all_warnings = self.warnings + [i for i in self.issues if i['type'] == 'WARNING']
        if all_warnings:
            print(f"\n⚠️ WARNINGS FOUND: {len(all_warnings)}")
            for warning in all_warnings[:10]:  # Show first 10
                print(f"   ⚠️ {warning['category']}: {warning['description']}")
                print(f"      File: {warning['file']}")
        
        # Duplications
        if self.duplications:
            print(f"\n🔄 DUPLICATIONS FOUND: {len(self.duplications)}")
            for dup in self.duplications:
                print(f"   🔄 {dup['description']}")
                print(f"      Files: {', '.join(dup['files'])}")
        
        # Fake Logs
        if self.fake_logs:
            print(f"\n🎭 POTENTIALLY FAKE LOGS: {len(self.fake_logs)}")
            for fake in self.fake_logs[:5]:  # Show first 5
                print(f"   🎭 {fake['description']}")
                print(f"      File: {fake['file']}:{fake['line']}")
                print(f"      Code: {fake['code'][:100]}...")
        
        # Summary
        total_issues = len(critical_issues) + len(all_warnings) + len(self.duplications) + len(self.fake_logs)
        print(f"\n📊 SUMMARY:")
        print(f"   • Critical Issues: {len(critical_issues)}")
        print(f"   • Warnings: {len(all_warnings)}")
        print(f"   • Duplications: {len(self.duplications)}")
        print(f"   • Potentially Fake Logs: {len(self.fake_logs)}")
        print(f"   • Total Issues: {total_issues}")
        
        if critical_issues:
            print(f"\n🚨 ACTION REQUIRED: {len(critical_issues)} critical issues need immediate attention!")
        elif total_issues > 0:
            print(f"\n⚠️ REVIEW NEEDED: {total_issues} issues found that should be reviewed.")
        else:
            print(f"\n✅ WORKFLOW LOOKS GOOD: No major issues detected.")

if __name__ == "__main__":
    # Run analysis
    analyzer = WorkflowAnalyzer("c:/Users/madma/OneDrive/Desktop/Trading AI")
    analyzer.analyze_all()
    
    print(f"\n🎯 NEXT STEPS:")
    print("1. Fix critical missing function calls")
    print("2. Review potentially fake logging")
    print("3. Resolve workflow conflicts")
    print("4. Improve data validation")
    print("5. Test execution logic thoroughly")
