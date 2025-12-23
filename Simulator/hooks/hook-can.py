# Specialized hook for python-can with can.interface support
from PyInstaller.utils.hooks import collect_all

# Collect everything from python-can
datas, binaries, hiddenimports = collect_all('can')

# Specifically ensure interface module is included
hiddenimports += [
    'can.interface',
    'can.interfaces',
    'can.bus',
    'can._interface',  # Sometimes internal module
    'can._bus',        # Internal bus module
]

# Force inclusion of interface module files
import can
import os

# Add any data files from can.interface
if hasattr(can, '__file__'):
    can_dir = os.path.dirname(can.__file__)
    interface_dir = os.path.join(can_dir, 'interface')
    if os.path.exists(interface_dir):
        for root, dirs, files in os.walk(interface_dir):
            for file in files:
                if file.endswith('.py'):
                    module_path = os.path.relpath(root, can_dir).replace('/', '.')
                    if module_path == '.':
                        module_name = 'can.interface'
                    else:
                        module_name = f'can.{module_path}.{file[:-3]}'
                    hiddenimports.append(module_name)

print(f"python-can hook: Added {len(hiddenimports)} hidden imports")
