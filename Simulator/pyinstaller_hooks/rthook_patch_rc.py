#!/usr/bin/env python3
"""
Runtime hook to fix python-can rc module issue in PyInstaller
"""

import sys
import os

# Only patch if we're running as a PyInstaller bundle
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    print("🔧 PyInstaller detected - patching can.rc module...")
    
    # Create mock rc module before can imports it
    class MockRc:
        class _Resource:
            def __init__(self):
                self.bus_settings = {}
                self._config = {}
            
            def __getattr__(self, name):
                # Return a dummy function
                def dummy(*args, **kwargs):
                    return None
                return dummy
        
        rc = _Resource()
    
    # Inject into sys.modules
    sys.modules['can.rc'] = MockRc
    print("✅ Patched can.rc module")
