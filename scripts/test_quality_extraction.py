import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from scanner.utils.delegator import delegate_extraction

luxury_text = """
STUNNING FEDERATION MASTERPIECE
This architecturally designed 45sq home sets a new standard in luxury living. 
Featuring Calacatta marble benchtops, Miele appliances, herringbone oak flooring, 
and soaring 3.5m ceilings. The master wing includes a bespoke dressing room and 
opulent ensuite with freestanding bath. Smart home automation, heated pool, and 
commercial grade double glazed windows complete this prestige offering.
"""

basic_text = """
ORIGINAL CONDITION - RENOVATORS DELIGHT
First time offered in 50 years. This classic brick veneer home offers a blank canvas 
for those looking to renovate or rebuild (STCA). Comprising 3 bedrooms, 1 bathroom, 
and original kitchen. Gas heating. Situated on a flat 650sqm block.
"""

print("--- Testing Luxury Text ---")
result_lux = delegate_extraction(luxury_text)
print(f"Detected Quality: {result_lux.get('finish_quality')}")
print(f"Features: {result_lux.get('features')}")

print("\n--- Testing Basic Text ---")
result_basic = delegate_extraction(basic_text)
print(f"Detected Quality: {result_basic.get('finish_quality')}")
print(f"Features: {result_basic.get('features')}")
