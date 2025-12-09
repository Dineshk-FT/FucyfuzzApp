# test_mdf4_fixed.py
import sys
import os
import numpy as np
import tempfile

print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")

try:
    import asammdf
    print(f"✓ asammdf imported: {asammdf.__version__}")
    
    from asammdf import MDF, Signal
    
    # Create test data with proper data types
    # Option 1: Use numeric data (recommended for CAN data)
    timestamps = np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    
    # For CAN frames, create numeric arrays
    can_ids = np.array([0x100, 0x101, 0x102, 0x103, 0x104], dtype=np.uint32)
    can_data_0 = np.array([0x11, 0x22, 0x33, 0x44, 0x55], dtype=np.uint8)
    can_data_1 = np.array([0xAA, 0xBB, 0xCC, 0xDD, 0xEE], dtype=np.uint8)
    
    # Create signals
    signal_id = Signal(
        samples=can_ids,
        timestamps=timestamps,
        name='CAN_ID',
        unit='-',
        comment='CAN Frame IDs'
    )
    
    signal_data0 = Signal(
        samples=can_data_0,
        timestamps=timestamps,
        name='CAN_Data_Byte0',
        unit='-',
        comment='CAN Data Byte 0'
    )
    
    signal_data1 = Signal(
        samples=can_data_1,
        timestamps=timestamps,
        name='CAN_Data_Byte1',
        unit='-',
        comment='CAN Data Byte 1'
    )
    
    # Create MDF file
    mdf = MDF()
    mdf.append([signal_id, signal_data0, signal_data1])
    
    test_file = tempfile.mktemp(suffix='.mf4')
    mdf.save(test_file)
    
    print(f"✓ MDF4 file created: {test_file}")
    print(f"✓ File size: {os.path.getsize(test_file)} bytes")
    
    # Option 2: If you need strings, encode them as bytes
    print("\nTesting string encoding...")
    
    # Create string data encoded as bytes
    string_data = ['Frame1', 'Frame2', 'Frame3', 'Frame4', 'Frame5']
    
    # Convert strings to bytes with consistent length
    max_len = max(len(s) for s in string_data)
    byte_array = np.zeros((len(string_data), max_len), dtype=np.uint8)
    
    for i, s in enumerate(string_data):
        byte_array[i, :len(s)] = np.frombuffer(s.encode('utf-8'), dtype=np.uint8)
    
    # Create signal with proper type
    signal_str = Signal(
        samples=byte_array,
        timestamps=timestamps,
        name='CAN_Frame_Strings',
        unit='-',
        comment='CAN Frame descriptions (UTF-8)'
    )
    
    mdf2 = MDF()
    mdf2.append(signal_str)
    
    test_file2 = tempfile.mktemp(suffix='.mf4')
    mdf2.save(test_file2)
    
    print(f"✓ String MDF4 file created: {test_file2}")
    
    # Clean up
    os.remove(test_file)
    os.remove(test_file2)
    
except ImportError as e:
    print(f"✗ Import failed: {e}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()