#!/bin/bash
# Activate the virtual environment
source /venv/bin/activate

# Debug information
echo "=== Debug Information ==="
echo "Python Version:"
python --version
echo "Working Directory:"
pwd
echo "PYTHONPATH:"
echo $PYTHONPATH
echo "Python sys.path:"
python -c "import sys; print('\n'.join(sys.path))"
echo "Contents of current directory:"
ls -la
echo "======================="

# Execute the command passed as arguments
exec "$@"