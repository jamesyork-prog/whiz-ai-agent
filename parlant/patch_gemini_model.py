#!/usr/bin/env python3
"""
Patch script to update Parlant SDK's hardcoded Gemini model references.

This script updates the gemini_service.py file in the Parlant SDK to use
gemini-2.5-flash instead of the deprecated gemini-1.5-flash model.
"""

import sys
from pathlib import Path


def patch_gemini_service():
    """Patch the Parlant SDK's gemini_service.py file."""
    
    # Find the gemini_service.py file
    site_packages = Path("/usr/local/lib/python3.11/site-packages")
    gemini_service_path = site_packages / "parlant" / "adapters" / "nlp" / "gemini_service.py"
    
    if not gemini_service_path.exists():
        print(f"❌ Could not find {gemini_service_path}")
        return False
    
    print(f"📝 Patching {gemini_service_path}")
    
    # Read the file
    content = gemini_service_path.read_text()
    
    # Track if we made any changes
    changes_made = False
    
    # Replace gemini-1.5-flash with gemini-2.5-flash
    if "gemini-1.5-flash" in content:
        content = content.replace("gemini-1.5-flash", "gemini-2.5-flash")
        changes_made = True
        print("  ✓ Replaced gemini-1.5-flash with gemini-2.5-flash")
    
    # Write back if changes were made
    if changes_made:
        gemini_service_path.write_text(content)
        print("✅ Patch applied successfully!")
        return True
    else:
        print("ℹ️  No changes needed - file already patched or pattern not found")
        return True


if __name__ == "__main__":
    success = patch_gemini_service()
    sys.exit(0 if success else 1)
