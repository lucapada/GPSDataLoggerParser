GNSS = {
    "constellations": [
        {
            "gnssId": 0,
            "gnss": "GPS",
            "configure": 1,
            "enable": 1,
            "minCh": 8,
            "maxCh": 16,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "G",
            "svIdFrom": 1,
            "svIdTo": 32
        },
        {
            "gnssId": 1,
            "gnss": "SBAS",
            "configure": 1,
            "enable": 0,
            "minCh": 1,
            "maxCh": 3,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "S",
            "svIdFrom": 120,
            "svIdTo": 158
        },
        {
            "gnssId": 2,
            "gnss": "Galileo",
            "configure": 1,
            "enable": 1,
            "minCh": 4,
            "maxCh": 8,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "E",
            "svIdFrom": 1,
            "svIdTo": 36
        },
        {
            "gnssId": 3,
            "gnss": "BeiDou",
            "configure": 1,
            "enable": 0,
            "minCh": 8,
            "maxCh": 16,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "B",
            "svIdFrom": 1,
            "svIdTo": 37
        },
        {
            "gnssId": 4,
            "gnss": "IMES",
            "configure": 1,
            "enable": 0,
            "minCh": 0,
            "maxCh": 8,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 3,
            "letter": "I",
            "svIdFrom": 1,
            "svIdTo": 10
        },
        {
            "gnssId": 5,
            "gnss": "QZSS",
            "configure": 1,
            "enable": 1,
            "minCh": 0,
            "maxCh": 3,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 5,
            "letter": "Q",
            "svIdFrom": 1,
            "svIdTo": 10
        },
        {
            "gnssId": 6,
            "gnss": "GLONASS",
            "configure": 1,
            "enable": 1,
            "minCh": 8,
            "maxCh": 14,
            "signals": b"\x01",
            "BitField 4 (pag 210)": 1,
            "letter": "R",
            "svIdFrom": 1,
            "svIdTo": 32
        }
    ],
    "chToUse": 32
}
