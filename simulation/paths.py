# Drone delivery flight paths over Kolkata.
# Waypoints are (lat, lon) tuples representing real corridors.

PATHS = {
    "ROUTE-EAST-WEST": {
        "description": "Howrah → BBD Bagh → Salt Lake → New Town  (east-west logistics corridor)",
        "waypoints": [
            (22.5848, 88.3426),  # Howrah Station
            (22.5726, 88.3639),  # BBD Bagh / Esplanade
            (22.5680, 88.3900),  # Park Circus / EM Bypass entry
            (22.5762, 88.4313),  # Salt Lake Sector V
            (22.5958, 88.4717),  # New Town Action Area I
        ],
    },
    "ROUTE-NORTH-SOUTH": {
        "description": "Dum Dum Airport → Ultadanga → Salt Lake → Park Street → Jadavpur  (N-S corridor)",
        "waypoints": [
            (22.6524, 88.3832),  # Dum Dum / Netaji Airport
            (22.5917, 88.3985),  # Ultadanga / EM Bypass
            (22.5762, 88.4313),  # Salt Lake Sector V
            (22.5490, 88.3528),  # Park Street
            (22.4996, 88.3740),  # Jadavpur
        ],
    },
    "ROUTE-SOUTH-LOOP": {
        "description": "BBD Bagh → Park Street → Tollygunge → Behala  (south city loop)",
        "waypoints": [
            (22.5726, 88.3639),  # BBD Bagh / Esplanade
            (22.5490, 88.3528),  # Park Street / AJC Bose Rd
            (22.4986, 88.3540),  # Tollygunge
            (22.4983, 88.3162),  # Behala Chowrasta
        ],
    },
}
