# expand_rom.py
# Genera la ROM expandida (8MB) a partir de la ROM original (4MB)
# La ROM expandida es la original duplicada (espejo)

ROM_INPUT  = 'Terrors (J) [M].ws'
ROM_OUTPUT = 'Terrors_expanded.ws'

with open(ROM_INPUT, 'rb') as f:
    rom = f.read()

assert len(rom) == 0x400000, f"ROM debe ser 4MB, tiene {len(rom):#x} bytes"

with open(ROM_OUTPUT, 'wb') as f:
    f.write(rom + rom)

print(f"ROM expandida generada: {ROM_OUTPUT} ({len(rom)*2:#x} bytes)")