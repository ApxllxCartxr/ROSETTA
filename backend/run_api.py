"""
ROSETTA API Startup Script
Run this file to start the FastAPI server.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if __name__ == "__main__":
    import uvicorn
    from api.utils.config_loader import load_config
    
    try:
        config = load_config()
        server_config = config.get("server", {})
        
        print("=" * 60)
        print("🚀 Starting ROSETTA API Server")
        print("=" * 60)
        print(f"Host: {server_config.get('host', '0.0.0.0')}")
        print(f"Port: {server_config.get('port', 8000)}")
        print(f"Docs: http://localhost:{server_config.get('port', 8000)}/docs")
        print("=" * 60)
        
        uvicorn.run(
            "api.main:app",
            host=server_config.get("host", "0.0.0.0"),
            port=server_config.get("port", 8000),
            reload=server_config.get("reload", True),
            log_level="info"
        )
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're in the backend/ directory")
        print("2. Check config.yaml exists in backend/api/")
        print("3. Verify all dependencies are installed: pip install -r api/requirements.txt")
        sys.exit(1)
