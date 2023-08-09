from colorama import init, Fore, Style
init()

nome_file = "COM26_bin.txt"  # sostituisci con il binario del file

with open("COM26_analysis.txt", "w") as output:
    with open(nome_file, "r") as file:
        blocchi = []
        blocco = ""
        while True:
            temp = file.read(1)
            if not temp: break
            blocco += temp
            if blocco.endswith("S"):
                blocchi.append(blocco.replace("S",""))
                blocco = ""

        for blocco in blocchi:
            # prendo la riga in binario
            data_BIN = blocco.strip()  # Rimuove spazi e caratteri di nuova linea
            # ogni 8 caratteri metto uno spazio
            riga_BIN = []
            riga_BYTE = []

            for i in range(0, len(data_BIN), 8):
                byte_BIN = data_BIN[i:i+8] 
                riga_BIN.append(byte_BIN)
                riga_BYTE.append(''.join(format(b, '02x') for b in (int(byte_BIN, 2).to_bytes(1, "big"))))
            
            bns = ""
            bys = ""
            bts = ""
            stampa = []
            k = 0
            for i in range(len(riga_BIN)):
                bns += riga_BIN[i] + " "
                bys += riga_BYTE[i] + " "
                try: 
                    if riga_BYTE[i] == "0a" or riga_BYTE[i] == "0d":
                        bts += repr(bytes.fromhex(riga_BYTE[i]).decode("ascii")) + " "
                    else: bts += bytes.fromhex(riga_BYTE[i]).decode("ascii") + " "
                except UnicodeDecodeError as e:
                    bts += "- "
                k += 1
                if (k == 8):
                    stampa.append(bns + "\t" + bys + "\t" + bts)
                    bns = ""
                    bys = ""
                    bts = ""
                    k = 0
            
            for j in range(len(stampa)):
                print(stampa[j], file=output)

            print("\nFINE BLOCCO\n ", file=output)
