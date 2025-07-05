#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify JasmineTool installation
"""

import sys
import os

def test_import():
    """Test importing JasmineTool modules"""
    try:
        import jasminetool
        print(f"✓ Successfully imported jasminetool (version: {jasminetool.__version__})")
        
        from jasminetool import UnifiedTaskRunner
        print("✓ Successfully imported UnifiedTaskRunner")
        
        from jasminetool import LocalMode, RemoteMode, SlurmMode, RemoteGpuMode
        print("✓ Successfully imported execution modes")
        
        from jasminetool import TmuxManager, ConfigManager
        print("✓ Successfully imported utility classes")
        
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_cli():
    """Test CLI functionality"""
    try:
        from jasminetool.cli import create_parser
        parser = create_parser()
        print("✓ Successfully created CLI parser")
        
        # Test help
        help_text = parser.format_help()
        if "jasminetool" in help_text:
            print("✓ CLI help text contains expected content")
        else:
            print("✗ CLI help text missing expected content")
            
        return True
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        from jasminetool.utils import ConfigManager
        
        # Test with example config if it exists
        example_config = "examples/agent_config.yaml"
        if os.path.exists(example_config):
            config = ConfigManager.load_config(example_config)
            print(f"✓ Successfully loaded example config with {len(config)} targets")
        else:
            print("⚠ Example config not found, skipping config test")
            
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing JasmineTool installation...")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_import),
        ("CLI Test", test_cli),
        ("Config Test", test_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  Failed: {test_name}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! JasmineTool is properly installed.")
        return 0
    else:
        print("❌ Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 