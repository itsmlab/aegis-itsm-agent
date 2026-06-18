# Copyright (c) 2025 Leopoldo Lara. All rights reserved.
# Licensed under the Apache License, Version 2.0.
#
"""Quick test to verify integration_module loads correctly"""
import sys
print("Testing integration_module import...")
import integration_module
print("OK - integration_module loaded successfully")
print(f"Tickets: {integration_module.stats['total']}")
cats = list(integration_module.stats['categories'].keys())
print(f"Categories: {cats}")
print(f"Classifier ready: {len(cats)} categories, {integration_module.stats['total']} tickets")