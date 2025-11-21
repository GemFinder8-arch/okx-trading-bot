#!/usr/bin/env python3
"""
Comprehensive scan of ALL bot files for fallback/fake values and data
"""

import os
import re
from pathlib import Path

def scan_all_fallbacks():
    """Scan all bot files for fallback/fake values."""
    
    print("🔍 COMPREHENSIVE SCAN: ALL FALLBACK/FAKE VALUES")
    print("=" * 70)
    
    # Define patterns to search for
    fallback_patterns = [
        # Direct fallback keywords
        (r'fallback', 'Fallback mechanisms'),
        (r'default.*=.*[0-9]', 'Default numeric values'),
        (r'return.*0\.[0-9]', 'Static decimal returns'),
        (r'return.*[0-9]+\.[0-9]', 'Static float returns'),
        
        # Hardcoded values
        (r'[0-9]{3,}', 'Large hardcoded numbers'),
        (r'\"[A-Z]{3,}\".*:.*[0-9]', 'Symbol mappings with values'),
        
        # Fake data indicators
        (r'placeholder', 'Placeholder values'),
        (r'mock|fake|dummy', 'Mock/fake data'),
        (r'hardcoded|static', 'Hardcoded/static references'),
        
        # Exception handling with returns
        (r'except.*:.*return.*[0-9]', 'Exception returns with values'),
        (r'if.*None.*return.*[0-9]', 'None checks with default values'),
        
        # Random/simulation
        (r'random\.|np\.random', 'Random value generation'),
        (r'simulate|artificial', 'Simulation/artificial data'),
    ]
    
    # Scan directories
    bot_dirs = [
        'trading_bot/analytics',
        'trading_bot/orchestration', 
        'trading_bot/execution',
        'trading_bot/coordination',
        'trading_bot/config',
        'trading_bot/infrastructure',
        'trading_bot/ml'
    ]
    
    total_issues = 0
    
    for bot_dir in bot_dirs:
        if not os.path.exists(bot_dir):
            continue
            
        print(f"\n📁 SCANNING: {bot_dir}")
        print("-" * 50)
        
        # Get all Python files
        py_files = list(Path(bot_dir).rglob("*.py"))
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                file_issues = []
                
                # Check each pattern
                for pattern, description in fallback_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = lines[line_num - 1].strip()
                        
                        # Skip comments and docstrings
                        if line_content.startswith('#') or '"""' in line_content or "'''" in line_content:
                            continue
                            
                        # Skip imports
                        if line_content.startswith('import ') or line_content.startswith('from '):
                            continue
                            
                        file_issues.append({
                            'pattern': description,
                            'line': line_num,
                            'content': line_content,
                            'match': match.group()
                        })
                
                # Report issues for this file
                if file_issues:
                    print(f"\n🚨 {py_file.name}:")
                    
                    for issue in file_issues[:10]:  # Limit to first 10 per file
                        print(f"   Line {issue['line']:3d}: {issue['pattern']}")
                        print(f"            {issue['content'][:80]}...")
                        print(f"            Match: '{issue['match']}'")
                        print()
                    
                    if len(file_issues) > 10:
                        print(f"   ... and {len(file_issues) - 10} more issues")
                    
                    total_issues += len(file_issues)
                else:
                    print(f"✅ {py_file.name}: Clean")
                        
            except Exception as exc:
                print(f"❌ Error reading {py_file}: {exc}")
    
    print("\n" + "=" * 70)
    print("🎯 SPECIFIC FALLBACK PATTERNS TO CHECK:")
    print()
    
    # Check specific known problematic patterns
    specific_checks = [
        ('return 0.5', 'Static 0.5 returns'),
        ('return 1.0', 'Static 1.0 returns'), 
        ('return None', 'None returns (check if should fail instead)'),
        ('except:', 'Bare except clauses'),
        ('try:', 'Try blocks (check exception handling)'),
        ('_fallback_', 'Fallback function names'),
        ('default_', 'Default value functions'),
        ('cache', 'Caching mechanisms'),
        ('risk_profile', 'Risk profile usage'),
        ('market_cap.*=.*[0-9]', 'Hardcoded market caps'),
        ('liquidity.*=.*0\.[0-9]', 'Hardcoded liquidity values'),
        ('confidence.*=.*0\.[0-9]', 'Hardcoded confidence values'),
        ('200.*candles', 'Hardcoded candle counts'),
        ('rsi_period.*=.*21', 'Hardcoded RSI periods'),
    ]
    
    print("🔍 TARGETED SEARCHES:")
    for pattern, desc in specific_checks:
        print(f"\n📋 {desc}:")
        
        # Search all files for this pattern
        found_files = []
        
        for bot_dir in bot_dirs:
            if not os.path.exists(bot_dir):
                continue
                
            py_files = list(Path(bot_dir).rglob("*.py"))
            
            for py_file in py_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if re.search(pattern, content, re.IGNORECASE):
                        found_files.append(str(py_file))
                        
                except:
                    continue
        
        if found_files:
            print(f"   ❌ Found in: {', '.join([Path(f).name for f in found_files])}")
        else:
            print(f"   ✅ Not found")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY:")
    print(f"Total potential issues found: {total_issues}")
    print()
    print("🎯 ACTION ITEMS:")
    print("1. Review each flagged file for actual fallback usage")
    print("2. Replace fallback values with None returns")
    print("3. Update exception handling to fail gracefully")
    print("4. Remove hardcoded default values")
    print("5. Eliminate fake/placeholder data")
    print()
    print("🏆 GOAL: 100% real live data, 0% fallback/fake values")

if __name__ == "__main__":
    scan_all_fallbacks()
