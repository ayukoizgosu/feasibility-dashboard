import os
import sys

sys.path.append(os.path.join(os.getcwd(), "src"))

from scanner.utils.delegator import delegate_extraction

# Text found from search    # test_extraction("address_placeholder", "actual_price")(Sold Listing)
text_1_13 = """
Contemporary Haven in Donvale.
Crafted for young professional families... highlighting modern elegance, convenience, high-end amenities.
The home features an open-plan kitchen and living area, equipped with Miele appliances, 
Caesarstone benchtops, and Polytec cabinetry. 
High ceilings, timber oak flooring, and double glazed windows throughout.
"""

print("--- Testing Sample Property (Manual Text) ---")
result = delegate_extraction(text_1_13)
print(f"Detected Quality: {result.get('finish_quality')}")
print(f"Features: {result.get('features')}")
