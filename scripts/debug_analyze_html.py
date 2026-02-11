import re

with open("debug_domain_playwright.html", "r", encoding="utf-8") as f:
    content = f.read()

# Look for patterns
print(f"Total length: {len(content)}")

# Check for specific classes
if "css-" in content:
    print("Found css- classes (styled components)")

matches = re.findall(r'class="([^"]*listing[^"]*)"', content)
print(f"Found {len(matches)} classes with 'listing':")
for m in set(matches[:10]):
    print(f" - {m}")

# Check for any data-testid
matches = re.findall(r'data-testid="([^"]*)"', content)
print(f"Found {len(matches)} data-testids (total):")
unique = sorted(list(set(matches)))
for m in unique:
    print(f" - {m}")
