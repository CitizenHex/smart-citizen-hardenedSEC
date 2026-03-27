#!/usr/bin/env python3
"""
Star Citizen Weapon vs Ship Damage Matrix Generator
Creates 2D tables showing which weapons can damage which ships
"""

import csv
from io import StringIO
from typing import List, Dict, Tuple

# Ship data from your provided table
SHIP_DATA = """
Idris P	173	139
Idris M	173	139
Hammerhead	152	101
Reclaimer	132	106
Polaris	132	106
Perseus	132	106
Carrack Expedition	120	64
Carrack	120	64
M2 Hercules Starlifter	110	80
C2 Hercules Starlifter	110	80
A2 Hercules Starlifter	110	80
890 Jump	108	86
Starlancer TAC	99	106
Terrapin Medic	97	52
Terrapin	97	52
Starfarer Gemini	95	101
Valkyrie	92	49
Paladin	92	49
Asgard	92	49
Starlancer MAX	90	96
Starfarer	90	96
Hull C	90	96
Caterpillar Pirate	90	80
Caterpillar	90	80
600i Touring	90	72
600i Executive Edition	90	72
600i	90	72
Mercury Star Runner	85	62
Hurricane	84	45
Guardian QI	84	62
Guardian MX	84	62
Guardian	84	62
F8C Lightning	84	45
F8A Lightning	84	45
Apollo Medivac	81	65
Zeus Mk II ES	77	62
Zeus Mk II CL	77	62
Vanguard Warden	77	62
Vanguard Sentinel	77	62
Vanguard Hoplite	77	62
Vanguard Harbinger	77	62
Stinger	77	50
Scorpius Antares	77	62
Scorpius	77	62
Retaliator	77	62
Redeemer	77	62
Hermes	77	62
Constellation Taurus	77	62
Constellation Phoenix Emerald	77	62
Constellation Phoenix	77	62
Constellation Aquila	77	62
Constellation Andromeda	77	62
C1 Spirit	77	56
Ares Star Fighter Ion	77	56
Ares Star Fighter Inferno	77	56
Apollo Triage	77	62
A1 Spirit	77	56
RAFT	70	62
MOTH	70	62
MOLE	70	62
Freelancer MIS	63	67
Freelancer MAX	63	67
Freelancer DUR	63	67
Freelancer	63	67
Corsair	63	56
400i	63	50
Prowler Utility	50	60
Prowler	50	60
Cutlass Steel	50	45
Cutlass Red	50	45
Cutlass Blue	50	45
Cutlass Black	50	45
Shiv	45	36
Gladiator	24	13
F7C-S Hornet Ghost Mk II	24	13
F7C-S Hornet Ghost Mk I	24	13
F7C-R Hornet Tracker Mk II	24	13
F7C-R Hornet Tracker Mk I	24	13
F7C-M Super Hornet Mk II	24	13
F7C-M Super Hornet Mk I	24	13
F7C-M Hornet Heartseeker Mk II	24	13
F7C-M Hornet Heartseeker Mk I	24	13
F7C Hornet Wildfire Mk I	24	13
F7C Hornet Mk II	24	13
F7C Hornet Mk I	24	13
F7A Hornet Mk II	24	13
F7A Hornet Mk I	24	13
Scythe	22	14
Meteor	22	18
Mantis	22	18
Glaive	22	14
San'tok.yāi	20	16
Sabre Raven	20	16
Sabre Peregrine	20	16
Sabre Firebird	20	16
Sabre Comet	20	16
Sabre	20	16
Defender	20	16
Vulture	18	16
Prospector	18	19
Hull A	18	19
Herald	18	16
Golem OX	18	16
Golem	18	16
Hawk	12	6
C8X Pisces Expedition	12	6
C8R Pisces Rescue	12	6
C8 Pisces	12	6
Arrow	12	6
Syulen	11	9
Salvation	11	9
Intrepid	11	8
Gladius Valiant	11	9
Gladius Pirate	11	9
Gladius	11	9
Eclipse	11	9
Blade	11	7
Avenger Warlock	11	9
Avenger Titan Renegade	11	9
Avenger Titan	11	9
Avenger Stalker	11	9
Aurora Mk II	11	9
Aurora Mk I SE	11	9
Aurora Mk I MR	11	9
Aurora Mk I LN	11	9
Aurora Mk I ES	11	9
Aurora Mk I CL	11	9
Aurora Mk I LX	11	9
Storm AA	10	8
Storm	10	8
SRV	10	9
Nova	10	8
Nomad	10	9
Mustang Omega	10	9
Mustang Gamma	10	9
Mustang Delta	10	9
Mustang Beta	10	9
Mustang Alpha	10	9
L-22 Alpha Wolf	10	8
L-21 Wolf	10	8
Khartu-al	10	9
Reliant Tana	9	10
Reliant Sen	9	10
Reliant Mako	9	10
Reliant Kore	9	10
Mule	9	8
M50 Interceptor	9	7
Fortune	9	10
Cutter Scout	9	8
Cutter Rambler	9	8
Cutter	9	8
Clipper	9	8
Buccaneer	9	8
85X Limited	9	7
350r	9	7
325a	9	7
315p	9	7
300i	9	7
135c	9	7
125a	9	7
100i	9	7
Talon Shrike	8	10
Talon	8	10
Ursa Medivac	6	4
Ursa Fortuna	6	4
Ursa	6	4
Spartan	6	3
Pulse LX	6	4
Pulse	6	4
Lynx	6	4
Centurion	6	3
Ballista Snowblind	6	3
Ballista Dunestalker	6	3
Ballista	6	3
X1 Velocity	5	4
X1 Force	5	4
X1	5	4
STV	5	4
ROC-DS	5	4
ROC	5	4
Razor LX	5	5
Razor EX	5	5
Razor	5	5
P-72 Archimedes Emerald	5	4
P-72 Archimedes	5	4
P-52 Merlin	5	4
Nox Kue	5	4
Nox	5	4
MTC	5	4
MPUV Tractor	5	4
MPUV Personnel	5	4
MPUV Cargo	5	4
MDC	5	4
HoverQuad	5	4
Fury MX	5	5
Fury LX	5	5
Fury	5	5
Dragonfly Yellowjacket	5	4
Dragonfly Star Kitten	5	4
Dragonfly	5	4
Cyclone TR	5	4
Cyclone RN	5	4
Cyclone RC	5	4
Cyclone MT	5	4
Cyclone AA	5	4
Cyclone	5	4
CSV-SM	5	4
PTV	5	4
"""

# Weapon data - name, alpha_min, biochem, distortion, energy, physical, stun, thermal
WEAPON_DATA = """
'WAR'	567	0	0	0	0	0	0
'WARLORD'	527	0	0	0	0	0	0
'WASP'	89	0	0	0	0	0	0
'WEAK'	73	0	0	0	0	0	0
'WHIP'	273	0	0	0	0	0	0
'WRATH'	972	0	0	0	0	0	0
10-Series Greatsword	73	0	0	0	84	0	0
11-Series Broadsword	109	0	0	0	109	0	0
9-Series Longsword	49	0	0	0	49	0	0
Absolution	720	0	0	720	0	0	0
AD4B	84	0	0	0	84	0	0
AD5B	127	0	0	0	127	0	0
AD6B	190	0	0	0	190	0	0
Ardor-1 Salvaged	73	0	0	0	0	0	0
Ardor-2 Salvaged	110	0	0	0	0	0	0
Ardor-3 Salvaged	152	0	0	0	0	0	0
Attrition-1	67	0	0	0	0	0	0
Attrition-2	100	0	0	0	0	0	0
Attrition-3	135	0	0	0	0	0	0
Attrition-4	202	0	0	0	0	0	0
Attrition-5	337	0	0	0	0	0	0
Attrition-6	505	0	0	0	0	0	0
ATVS	27	0	28	0	0	0	0
Axiom L-22	85	0	0	0	0	0	0
Breakneck S4	52	0	0	0	52	0	0
BRVS	54	0	0	0	54	0	0
C-788	325	0	0	0	325	0	0
CF-117 Bulldog	17	0	0	0	0	0	0
CF-227 Badger	26	0	0	0	0	0	0
CF-337 Panther	44	0	0	0	0	0	0
CF-447 Rhino	65	0	0	0	0	0	0
CF-557 Galdereen	98	0	0	0	0	0	0
CF-667 Mammoth	147	0	0	0	0	0	0
Condemnation	1040	0	0	1040	0	0	0
Conqueror-7	4000	0	0	0	4000	0	0
CVSA	162	0	0	0	162	0	0
Deadbolt I	203	0	0	0	203	0	0
Deadbolt II	303	0	0	0	303	0	0
Deadbolt III	455	0	0	0	455	0	0
Deadbolt IV	683	0	0	0	683	0	0
Deadbolt V	1024	0	0	0	1024	0	0
Deadbolt VI	1537	0	0	0	1537	0	0
Destroyer Mass Driver	288320	0	0	0	288320	0	0
Dominance-1	504	0	0	504	0	0	0
Dominance-2	792	0	0	792	0	0	0
Dominance-3	1116	0	0	1116	0	0	0
DR Model-XJ1	26	0	25	0	0	0	0
DR Model-XJ2	39	0	28	0	0	0	0
DR Model-XJ3	58	0	30	0	0	0	0
Draugar	142	0	0	0	142	0	0
EVSD	81	0	28	0	0	0	0
FL-11	49	0	0	0	0	0	0
FL-22	74	0	0	0	0	0	0
FL-33	111	0	0	0	0	0	0
GVSR	100	0	0	0	0	0	0
Havoc	374	0	0	0	374	0	0
Hellion	560	0	0	0	560	0	0
Jericho	150	0	0	0	0	0	0
Jericho X	150	0	0	0	0	0	0
Jericho XL (FireStorm)	150	0	0	0	0	0	0
Jericho XL (Hurston)	150	0	0	0	0	0	0
Leonids	1600	0	0	0	1600	0	0
Liberator	150	0	0	0	0	0	0
Liberator Prime	150	0	0	0	0	0	0
Liberator Ultra	150	0	0	0	0	0	0
Lightstrike I	49	0	0	0	0	0	0
Lightstrike II	74	0	0	0	0	0	0
Lightstrike III	111	0	0	0	0	0	0
Lightstrike IV	166	0	0	0	0	0	0
Lightstrike V	249	0	0	0	0	0	0
Lightstrike VI	374	0	0	0	0	0	0
M10A	3114	0	0	0	0	0	0
M11A	4670	0	0	0	0	0	0
M2C Swarm	10	0	0	0	0	0	0
M3A	182	0	0	0	0	0	0
M4A	273	0	0	0	0	0	0
M5A	410	0	0	0	0	0	0
M6A	615	0	0	0	0	0	0
M7A	922	0	0	0	0	0	0
M8A	1383	0	0	0	0	0	0
M9A	2076	0	0	0	0	0	0
Mantis GT-220	19	0	0	0	19	0	0
Maris	3400	0	0	0	3400	0	0
MRX Torrent	18	0	0	0	18	0	0
MVSA	273	0	0	0	0	0	0
NDB-26	38	0	0	0	0	0	0
NDB-28	57	0	0	0	0	0	0
NDB-30	86	0	0	0	0	0	0
NN-13	101	0	0	0	0	0	0
NN-14	153	0	0	0	0	0	0
NN-15	221	0	0	0	0	0	0
NV57	163	0	0	0	163	0	0
Omnisky III	97	0	0	0	0	0	0
Omnisky IX	219	0	0	0	0	0	0
Omnisky VI	146	0	0	0	0	0	0
Omnisky XII	328	0	0	0	0	0	0
Omnisky XV	492	0	0	0	0	0	0
Omnisky XVIII	738	0	0	0	0	0	0
Predator	840	0	0	0	840	0	0
PyroBurst	396	0	0	396	0	0	0
Quarreler	219	0	0	0	0	0	0
Reign-3	350	0	0	0	0	0	0
Relentless L-21	63	0	0	0	63	0	0
Revenant	63	0	0	0	63	0	0
RSI Medusa	5400	0	0	0	5400	0	0
Salvation	480	0	0	480	0	0	0
Scorpion GT-215	13	0	0	0	13	0	0
SF7B	292	0	0	0	292	0	0
SF7E	5150	0	0	0	0	0	0
Singe-1	203	0	0	0	203	0	0
Singe-2	473	0	0	0	473	0	0
Singe-3	1013	0	0	0	1013	0	0
Slayer	32000	0	0	0	32000	0	0
Sledge I Mass Driver	225	0	0	0	225	0	0
Sledge II Mass Driver	525	0	0	0	525	0	0
Sledge III Mass Driver	1125	0	0	0	1125	0	0
Strife Mass Driver	525	0	0	0	525	0	0
Suckerpunch	81	0	25	0	0	0	0
Suckerpunch-L	122	0	28	0	0	0	0
Suckerpunch-XL	183	0	30	0	0	0	0
SW16BR1 Buzzsaw	36	0	0	0	36	0	0
SW16BR2 Sawbuck	54	0	0	0	54	0	0
SW16BR3 Shredder	81	0	0	0	81	0	0
Tarantula GT-870 Mk 1	61	0	0	0	61	0	0
Tarantula GT-870 Mk 2	91	0	0	0	91	0	0
Tarantula GT-870 Mk 3	137	0	0	0	137	0	0
Thlilye Laser	17	0	0	0	0	17	0
Tigerstrike T-19P	23	0	0	0	23	0	0
TMSB-5 Gatling	53	0	0	0	53	0	0
Tormenter S3	40	0	0	0	0	0	0
Yebira I	150	0	0	0	0	0	0
Yebira II	150	0	0	0	0	0	0
YellowJacket GT-210	8	0	0	0	8	0	0
Yeng'tu	36	0	0	0	0	0	0
"""

def parse_ships(data_str: str) -> List[Tuple[str, int, int]]:
    """Parse ship data: (name, deflection_physical, deflection_energy)"""
    ships = []
    for line in data_str.strip().split('\n'):
        if line.strip():
            parts = line.split('\t')
            if len(parts) == 3:
                name = parts[0].strip()
                try:
                    phys = int(parts[1].strip())
                    energy = int(parts[2].strip())
                    ships.append((name, phys, energy))
                except ValueError:
                    continue
    return ships

def parse_weapons(data_str: str) -> List[Tuple[str, int, int, int, int, int, int, int]]:
    """Parse weapon data: (name, alpha, biochem, distortion, energy, physical, stun, thermal)"""
    weapons = []
    for line in data_str.strip().split('\n'):
        if line.strip():
            parts = line.split('\t')
            if len(parts) >= 8:
                name = parts[0].strip().replace("'", "").replace('"', "")
                try:
                    alpha = int(parts[1].strip())
                    biochem = int(parts[2].strip())
                    distortion = int(parts[3].strip())
                    energy = int(parts[4].strip())
                    physical = int(parts[5].strip())
                    stun = int(parts[6].strip())
                    thermal = int(parts[7].strip())
                    weapons.append((name, alpha, biochem, distortion, energy, physical, stun, thermal))
                except (ValueError, IndexError):
                    continue
    return weapons

def generate_html(ships: List, weapons: List) -> str:
    """Generate HTML tables for weapon vs ship damage"""

    # Separate weapons by type and sort by alpha damage
    physical_weapons = [(n, a) for n, a, _, _, _, p, _, _ in weapons if p > 0]
    energy_weapons = [(n, a) for n, a, _, _, e, _, _, _ in weapons if e > 0]
    distortion_weapons = [(n, a) for n, a, _, d, _, _, _, _ in weapons if d > 0]

    physical_weapons.sort(key=lambda x: x[1], reverse=True)
    energy_weapons.sort(key=lambda x: x[1], reverse=True)
    distortion_weapons.sort(key=lambda x: x[1], reverse=True)

    # Sort ships by deflection (ascending - most vulnerable first)
    ships_by_phys = sorted(ships, key=lambda x: x[1])
    ships_by_energy = sorted(ships, key=lambda x: x[2])

    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Star Citizen Weapon vs Ship Damage Matrix</title>
    <style>
        * { font-family: Arial, sans-serif; }
        body { padding: 20px; background: #1a1a1a; color: #fff; }
        h1, h2 { color: #4CAF50; }
        table {
            border-collapse: collapse;
            margin: 20px 0;
            background: #222;
            border: 1px solid #444;
        }
        th {
            background: #333;
            padding: 8px;
            text-align: left;
            border: 1px solid #444;
            font-weight: bold;
            color: #4CAF50;
        }
        td {
            padding: 6px 8px;
            border: 1px solid #333;
            text-align: center;
        }
        .ship-name { text-align: left; background: #2a2a2a; font-weight: bold; }
        .weapon-name { text-align: left; background: #2a2a2a; }
        .can-damage { background: #4CAF50; color: #000; font-weight: bold; }
        .cannot-damage { background: #555; color: #999; }
        .deflection { color: #FFB74D; font-size: 0.85em; }
        .alpha { color: #81C784; font-size: 0.85em; }
        .info { background: #2a2a2a; padding: 15px; margin: 20px 0; border-left: 4px solid #4CAF50; }
    </style>
</head>
<body>
    <h1>⚔️ Star Citizen Weapon vs Ship Damage Matrix</h1>
    <div class="info">
        <strong>How to read:</strong> A weapon damages a ship if Alpha Damage ≥ Ship Deflection<br>
        <strong>Green cells:</strong> Weapon can damage ship armor<br>
        <strong>Gray cells:</strong> Weapon cannot damage ship armor
    </div>
"""

    # Generate tables for each damage type
    damage_types = [
        ("PHYSICAL DAMAGE", physical_weapons, ships_by_phys, 1),
        ("ENERGY DAMAGE", energy_weapons, ships_by_energy, 2),
        ("DISTORTION DAMAGE", distortion_weapons, ships_by_phys, 1),
    ]

    for damage_type_name, weapons_list, ships_list, deflection_idx in damage_types:
        if not weapons_list:
            continue

        html += f"<h2>{damage_type_name}</h2>\n"
        html += "<table>\n<tr><th>Ship (sorted by deflection)</th>"

        for weapon_name, alpha in weapons_list:
            html += f"<th title='Alpha Damage: {alpha}'>{weapon_name[:20]}<br><span class='alpha'>{alpha}</span></th>"

        html += "</tr>\n"

        for ship_name, phys_def, energy_def in ships_list:
            deflection = phys_def if deflection_idx == 1 else energy_def
            html += f"<tr><td class='ship-name'>{ship_name}<br><span class='deflection'>DEF: {deflection}</span></td>"

            for weapon_name, alpha in weapons_list:
                if alpha >= deflection:
                    html += f"<td class='can-damage'>✓</td>"
                else:
                    html += f"<td class='cannot-damage'>✗</td>"

            html += "</tr>\n"

        html += "</table>\n"

    html += """
    <div class="info">
        <strong>Legend:</strong><br>
        ✓ = Weapon can damage ship (Alpha ≥ Deflection)<br>
        ✗ = Weapon cannot damage ship (Alpha < Deflection)
    </div>
</body>
</html>
"""

    return html

def main():
    ships = parse_ships(SHIP_DATA)
    weapons = parse_weapons(WEAPON_DATA)

    print(f"Loaded {len(ships)} ships and {len(weapons)} weapons")

    html = generate_html(ships, weapons)

    output_file = "weapon_ship_damage_matrix.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated {output_file}")
    print("\nExample ships:")
    for ship in ships[:5]:
        print(f"  {ship[0]}: Physical DEF={ship[1]}, Energy DEF={ship[2]}")

    print("\nExample weapons:")
    for weapon in weapons[:5]:
        print(f"  {weapon[0]}: Alpha={weapon[1]}")

if __name__ == "__main__":
    main()