"""Seed script: prints NOGA code reference for target industries.

This serves as documentation for the NOGA codes used in classification.
"""

NOGA_CODES = {
    "41.10": "Erschliessung von Grundstücken / Bauträger",
    "41.20": "Bau von Gebäuden / Hochbau",
    "42.11": "Bau von Strassen",
    "42.12": "Bau von Bahnverkehrsstrecken",
    "42.13": "Brücken- und Tunnelbau",
    "42.21": "Rohrleitungstiefbau, Brunnenbau und Kläranlagenbau",
    "42.22": "Kabelnetzleitungstiefbau",
    "42.91": "Wasserbau",
    "42.99": "Sonstiger Tiefbau",
    "43.11": "Abbrucharbeiten",
    "43.12": "Vorbereitende Baustellenarbeiten",
    "43.13": "Test- und Suchbohrung",
    "43.21": "Elektroinstallation",
    "43.22": "Gas-, Wasser-, Heizungs- sowie Lüftungs- und Klimainstallation",
    "43.29": "Sonstige Bauinstallation",
    "43.31": "Anbringen von Stuckaturen, Gipserei und Verputzerei",
    "43.32": "Bautischlerei und -schlosserei",
    "43.33": "Fussboden-, Fliesen- und Plattenlegerei, Tapeziererei",
    "43.34": "Malerei und Glaserei",
    "43.39": "Sonstiger Ausbau a.n.g.",
    "43.91": "Dachdeckerei und Zimmerei",
    "43.99": "Sonstige spezialisierte Bautätigkeiten a.n.g.",
}

# Primary target trades for initial focus
PRIMARY_TARGETS = ["43.31", "43.34"]

# Secondary targets for future expansion
SECONDARY_TARGETS = ["43.21", "43.22", "43.32", "43.33", "43.39", "43.91"]


def main():
    print("=== NOGA Codes: Baugewerbe ===\n")
    print("--- PRIMARY TARGETS (Phase 1) ---")
    for code in PRIMARY_TARGETS:
        print(f"  {code}: {NOGA_CODES[code]}")

    print("\n--- SECONDARY TARGETS (Future) ---")
    for code in SECONDARY_TARGETS:
        print(f"  {code}: {NOGA_CODES[code]}")

    print(f"\n--- ALL CONSTRUCTION CODES ---")
    for code, desc in sorted(NOGA_CODES.items()):
        print(f"  {code}: {desc}")


if __name__ == "__main__":
    main()
