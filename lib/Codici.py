def ublox_UBX_codes(classIn, idIn):
    classOut = 0
    idOut = 0
    if (classIn == "AID"):
        classOut = b"\x0b"
        if (idIn == "HUI"): idOut = b"\x02"
        if (idIn == "EPH"): idOut = b"\x31"

    if (classIn == "CFG"):
        classOut = b"\x06"
        if (idIn == "MSG"): idOut = b"\x01"
        if (idIn == "NMEA"): idOut = b"\x17"
        if (idIn == "RATE"): idOut = b"\x08"
        if (idIn == "CFG"): idOut = b"\x09"
        if (idIn == "GNSS"): idOut = b"\x3e"

    if (classIn == "ACK"):
        classOut = b"\x05"
        if (idIn == "ACK"): idOut = b"\x01"
        if (idIn == "NAK"): idOut = b"\x00"

    if (classIn == "RXM"):
        classOut = b"\x02"
        if (idIn == "RAWX"): idOut = b"\x15"
        if (idIn == "SFRBX"): idOut = b"\x13"

    if (classIn == "NAV"):
        classOut = b"\x01"
        if (idIn == "TIMEBDS"): idOut = b"\x24"
        if (idIn == "TIMEGAL"): idOut = b"\x25"
        if (idIn == "TIMEGLO"): idOut = b"\x23"
        if (idIn == "TIMEGPS"): idOut = b"\x20"
        if (idIn == "TIMEUTC"): idOut = b"\x21"

    if (classIn == "NMEA"):
        classOut = b"\xf0"
        if (idIn == "GGA"): idOut = b"\x00"
        if (idIn == "GLL"): idOut = b"\x01"
        if (idIn == "GSA"): idOut = b"\x02"
        if (idIn == "GSV"): idOut = b"\x03"
        if (idIn == "RMC"): idOut = b"\x04"
        if (idIn == "VTG"): idOut = b"\x05"
        if (idIn == "GRS"): idOut = b"\x06"
        if (idIn == "GST"): idOut = b"\x07"
        if (idIn == "ZDA"): idOut = b"\x08"
        if (idIn == "GBS"): idOut = b"\x09"
        if (idIn == "DTM"): idOut = b"\x0a"

        if (idIn == "GBQ"): idOut = b"\x44"
        if (idIn == "GLQ"): idOut = b"\x43"
        if (idIn == "GNQ"): idOut = b"\x42"
        if (idIn == "GNS"): idOut = b"\x0d"
        if (idIn == "GPQ"): idOut = b"\x40"
        if (idIn == "THS"): idOut = b"\x03"
        if (idIn == "TXT"): idOut = b"\x41"
        if (idIn == "VLW"): idOut = b"\x0f"

    if (classIn == "PUBX"):
        classOut = b"\xf1"
        if (idIn == "CONFIG"): idOut = b"\x41"
        if (idIn == "POSITION"): idOut = b"\x00"
        if (idIn == "RATE"): idOut = b"\x40"
        if (idIn == "SVSTATUS"): idOut = b"\x03"
        if (idIn == "TIME"): idOut = b"\x04"

    return (classOut, idOut)