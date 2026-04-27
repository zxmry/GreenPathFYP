"""Entry point for the GreenPath Flask application."""

import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Create necessary folders
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)

    print("=" * 60)
    print("🚀 GREENPATH DELIVERY OPTIMIZER")
    print("=" * 60)
    print("📁 System Check:")
    print(f"   • Working directory: {os.getcwd()}")
    print(
        f"   • run.py: {'✅ Found' if os.path.exists('run.py') else '❌ Missing'}"
    )
    print(
        f"   • templates/index.html: "
        f"{'✅ Found' if os.path.exists('templates/index.html') else '❌ Missing'}"
    )
    print(
        f"   • static/ folder: "
        f"{'✅ Found' if os.path.exists('static') else '❌ Missing'}"
    )
    print(
        f"   • app/services/geo_service.py: "
        f"{'✅ Found' if os.path.exists('app/services/geo_service.py') else '❌ Missing'}"
    )
    print(
        f"   • app/solver/genetic.py: "
        f"{'✅ Found' if os.path.exists('app/solver/genetic.py') else '❌ Missing'}"
    )
    print("=" * 60)
    print("💡 Algorithm Features:")
    print("   • Real original route calculation (user's input order)")
    print("   • Genetic Algorithm optimization")
    print("   • CO₂ and time savings based on actual distances")
    print("   • Detailed route visualization data")
    print("=" * 60)

    app.run(debug=True, port=5000)

