from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from localization_tools import Entry, GlobalIniData  # noqa: E402
from transport_overlay_source import generate_transport_overlay_data  # noqa: E402


class TransportOverlaySourceTests(unittest.TestCase):
    def test_generates_route_suffix_for_single_pickup_and_dropoff(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Delivery_Run_Title_001", value="Run goods"),
                Entry(
                    key="Delivery_Run_Desc_001",
                    value="Move the cargo from <EM4>~mission(Location|Address)</EM4> to <EM4>~mission(Destination|Address)</EM4>.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["Delivery_Run_Title_001"],
            " <EM4>| ~mission(Location|name) > ~mission(Destination|name)</EM4>",
        )

    def test_generates_from_suffix_for_location_only_transport(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Salvage_Run_Title_001", value="Salvage run"),
                Entry(
                    key="Salvage_Run_Desc_001",
                    value="Head to <EM4>~mission(Location|Address)</EM4> and recover what you can.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["Salvage_Run_Title_001"],
            " <EM4>| ##transport_from## ~mission(Location|name)</EM4>",
        )

    def test_skips_non_transport_titles(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Assault_Title_001", value="Attack"),
                Entry(
                    key="Assault_Desc_001",
                    value="Head to <EM4>~mission(Location|Address)</EM4> and destroy the target.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(generated.mapping, {})

    def test_title_key_taxonomy_handles_multi_to_single_without_literal_route_text(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="LingFamily_HaulCargo_MultiToSingle_title", value="Ling title"),
                Entry(
                    key="LingFamily_HaulCargo_MultiToSingle_desc",
                    value="PICK UP LOCATIONS (ANY ORDER)\\n\\n~mission(MultiToSingleToken)",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["LingFamily_HaulCargo_MultiToSingle_title"],
            " <EM4>| ##transport_to## ~mission(Destination|name)</EM4>",
        )

    def test_title_key_taxonomy_handles_single_to_multi_without_literal_route_text(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Covalex_HaulCargo_SingleToMulti_title", value="Covalex title"),
                Entry(
                    key="Covalex_HaulCargo_SingleToMulti_desc",
                    value="Deliver to several places later.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["Covalex_HaulCargo_SingleToMulti_title"],
            " <EM4>| ##transport_from## ~mission(Location|name)</EM4>",
        )

    def test_generates_from_suffix_for_multi_destination_patterns(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Cargo_Multi_Title_001", value="Cargo run"),
                Entry(
                    key="Cargo_Multi_Desc_001",
                    value="Pick up at <EM4>~mission(Location|Address)</EM4> and deliver to <EM4>~mission(Destination1|Address)</EM4>.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["Cargo_Multi_Title_001"],
            " <EM4>| ##transport_from## ~mission(Location|name)</EM4>",
        )

    def test_generates_to_suffix_for_multi_pickup_patterns(self) -> None:
        english_data = GlobalIniData(
            entries=[
                Entry(key="Cargo_MultiPickup_Title_001", value="Cargo run"),
                Entry(
                    key="Cargo_MultiPickup_Desc_001",
                    value="Collect cargo at <EM4>~mission(Location1|Address)</EM4> and <EM4>~mission(Location2|Address)</EM4>, then bring it to <EM4>~mission(Destination|Address)</EM4>.",
                ),
            ],
            mapping={},
        )

        generated = generate_transport_overlay_data(english_data=english_data)

        self.assertEqual(
            generated.mapping["Cargo_MultiPickup_Title_001"],
            " <EM4>| ##transport_to## ~mission(Destination|name)</EM4>",
        )


if __name__ == "__main__":
    unittest.main()
