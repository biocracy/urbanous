
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

print("Attempting to import main...")
try:
    from main import app
    print("SUCCESS: Imported main")
except Exception as e:
    print(f"FAILURE: Could not import main: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import outlets router...")
try:
    from routers import outlets
    print("SUCCESS: Imported outlets router")
except Exception as e:
    print(f"FAILURE: Could not import outlets router: {e}")
    import traceback
    traceback.print_exc()
