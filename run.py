#!/usr/bin/env python3
"""
Spúšťací skript pre PL1 Learning System.

Tento skript spúšťa backend aplikáciu pomocou Uvicorn servera.
"""

import uvicorn
import os
import sys

def main():
    """Spustí backend aplikáciu."""
    # Pridaj cestu k backend adresáru do sys.path
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if backend_dir not in sys.path:
        sys.path.append(backend_dir)
    
    # Spusti Uvicorn server
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main() 