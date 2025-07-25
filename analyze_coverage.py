import re
import subprocess

# Run coverage and capture output
result = subprocess.run(
    ["uv", "run", "pytest", "tests/unit/", "--cov=create_project", "--cov-report=term"],
    capture_output=True, text=True
)

# Parse coverage data
coverage_data = {}
for line in result.stdout.split("\n"):
    match = re.match(r"(create_project/[\w/]+\.py)\s+(\d+)\s+(\d+)\s+(\d+)%", line)
    if match:
        path, stmts, miss, cover = match.groups()
        coverage_data[path] = {
            "statements": int(stmts),
            "missing": int(miss),
            "coverage": int(cover)
        }

# Categorize modules
categories = {
    "Core Engine": [],
    "AI Module": [],
    "Templates": [],
    "GUI": [],
    "Config": [],
    "Utils": [],
    "Resources": [],
    "Other": []
}

for path, data in coverage_data.items():
    if "/core/" in path:
        categories["Core Engine"].append((path, data))
    elif "/ai/" in path:
        categories["AI Module"].append((path, data))
    elif "/templates/" in path:
        categories["Templates"].append((path, data))
    elif "/gui/" in path:
        categories["GUI"].append((path, data))
    elif "/config/" in path:
        categories["Config"].append((path, data))
    elif "/utils/" in path:
        categories["Utils"].append((path, data))
    elif "/resources/" in path:
        categories["Resources"].append((path, data))
    else:
        categories["Other"].append((path, data))

# Print summary
print("Unit Test Coverage Report by Module Category")
print("=" * 70)
print()

total_stmts = 0
total_covered = 0

for category, modules in categories.items():
    if not modules:
        continue

    cat_stmts = sum(m[1]["statements"] for m in modules)
    cat_covered = sum(m[1]["statements"] - m[1]["missing"] for m in modules)
    cat_coverage = (cat_covered / cat_stmts * 100) if cat_stmts > 0 else 0

    total_stmts += cat_stmts
    total_covered += cat_covered

    print(f"{category}:")
    print(f"  Overall: {cat_covered}/{cat_stmts} statements ({cat_coverage:.1f}% coverage)")

    # Sort modules by coverage
    sorted_modules = sorted(modules, key=lambda x: x[1]["coverage"])

    # Show lowest coverage modules
    print("  Lowest coverage modules:")
    for path, data in sorted_modules[:3]:
        module = path.split("/")[-1]
        print(f"    - {module}: {data['coverage']}%")

    print()

print("-" * 70)
print(f"TOTAL PROJECT COVERAGE: {total_covered}/{total_stmts} statements ({total_covered/total_stmts*100:.1f}%)")
print()

# Identify high-priority modules for testing
print("High Priority Modules for Testing (low coverage, high importance):")
print("-" * 70)

priority_modules = [
    ("create_project/core/project_generator.py", "Core project generation logic"),
    ("create_project/templates/renderers.py", "Template rendering system"),
    ("create_project/ai/ai_service.py", "AI service integration"),
    ("create_project/config/config_manager.py", "Configuration management"),
    ("create_project/gui/wizard/wizard.py", "Main GUI wizard"),
]

for module, description in priority_modules:
    if module in coverage_data:
        data = coverage_data[module]
        print(f"- {module.split('/')[-1]}: {data['coverage']}% - {description}")
