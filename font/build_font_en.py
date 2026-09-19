"""
build_font_en.py
Edita o agrega glifos en font_en.bin

IMPORTANTE: la pantalla WonderSwan esta rotada 90 grados.
Los glifos deben dibujarse en orientacion NORMAL (como se leen).
El script aplica la rotacion 90 grados horario automaticamente.

Uso: editar GLIFOS_NUEVOS con el caracter y su diseno 5x5
     5 filas de 5 bits (usar 0 y 1, MSB primero)
     Luego correr: python font/build_font_en.py

Caracteres disponibles:
' ABCDEFGHIJKLMNOPQRSTUVWXYZ.,?!-12@:'

Fuente base: mcufont 5x5 (https://maurycyz.com/projects/mcufont/)
"""
FUENTE_BIN = 'font/font_en.bin'
CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ.,?!-1234567890@:'"

# Todos los glifos de mcufont 5x5 ya incluidos
GLIFOS_BASE = {
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    'A': [0b01110, 0b10001, 0b11111, 0b10001, 0b10001],
    'B': [0b11110, 0b10001, 0b11110, 0b10001, 0b11110],
    'C': [0b01111, 0b10000, 0b10000, 0b10000, 0b01111],
    'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b11110],
    'E': [0b11111, 0b10000, 0b11100, 0b10000, 0b11111],
    'F': [0b11111, 0b10000, 0b11100, 0b10000, 0b10000],
    'G': [0b01111, 0b10000, 0b10011, 0b10001, 0b01111],
    'H': [0b10001, 0b10001, 0b11111, 0b10001, 0b10001],
    'I': [0b11111, 0b00100, 0b00100, 0b00100, 0b11111],
    'J': [0b11111, 0b00010, 0b00010, 0b10010, 0b01100],
    'K': [0b10010, 0b10100, 0b11000, 0b10100, 0b10010],
    'L': [0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    'M': [0b11111, 0b10101, 0b10101, 0b10001, 0b10001],
    'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001],
    'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
    'P': [0b11110, 0b10001, 0b11110, 0b10000, 0b10000],
    'Q': [0b01110, 0b10001, 0b10001, 0b10010, 0b01101],
    'R': [0b11110, 0b10001, 0b11110, 0b10010, 0b10001],
    'S': [0b01111, 0b10000, 0b01110, 0b00001, 0b11110],
    'T': [0b11111, 0b00100, 0b00100, 0b00100, 0b00100],
    'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'V': [0b10001, 0b10001, 0b01010, 0b01010, 0b00100],
    'W': [0b10001, 0b10001, 0b10101, 0b10101, 0b11011],
    'X': [0b10001, 0b01010, 0b00100, 0b01010, 0b10001],
    'Y': [0b10001, 0b01010, 0b00100, 0b00100, 0b00100],
    'Z': [0b11111, 0b00010, 0b00100, 0b01000, 0b11111],
    '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b01000],
    ',': [0b00000, 0b00000, 0b00000, 0b00100, 0b01000],
    '?': [0b01110, 0b10001, 0b00110, 0b00000, 0b00100],
    '!': [0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
    '-': [0b00000, 0b00000, 0b01110, 0b00000, 0b00000],
    '1': [0b01100, 0b10100, 0b00100, 0b00100, 0b11111],
    '2': [0b01110, 0b10001, 0b00110, 0b01000, 0b11111],
    '3': [0b11111, 0b00001, 0b01110, 0b00001, 0b11110],
    '4': [0b10010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b01110, 0b00001, 0b11110],
    '6': [0b01110, 0b10000, 0b11110, 0b10001, 0b01110],
    '7': [0b11111, 0b00010, 0b00100, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b01110, 0b10001, 0b01110],
    '9': [0b11111, 0b10001, 0b11111, 0b00001, 0b00001],
    '0': [0b01110, 0b10001, 0b10101, 0b10001, 0b01110],
    '@': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000],  # invisible
    ':': [0b00000, 0b01000, 0b00000, 0b01000, 0b00000],
}

# Agregar o modificar glifos aqui (misma formato 5x5 bits):
GLIFOS_NUEVOS = {
    "'": [0b00100, 0b00100, 0b00000, 0b00000, 0b00000],
}

def make_8x8_from_5x5(rows5):
    grid = [[0]*8 for _ in range(8)]
    for r, row in enumerate(rows5):
        for c in range(5):
            bit = (row >> (4-c)) & 1
            grid[r+1][c+1] = bit
    return grid

def rotar_90_horario(grid):
    rotado = [[0]*8 for _ in range(8)]
    for i in range(8):
        for j in range(8):
            rotado[j][7-i] = grid[i][j]
    return rotado

def grid_to_glyph(grid):
    result = []
    for row in grid:
        p = 0
        for bit, v in enumerate(row):
            if v:
                p |= (1 << (7-bit))
        result += [p, p]
    return bytes(result)

def mostrar_glifo(data, char):
    idx = CHARS.index(char)
    offset = idx * 16
    print(f'Glifo {repr(char)} (idx={idx}):')
    for row in range(8):
        p = data[offset+row*2]
        line = ''.join('#' if (p>>(7-b))&1 else ' ' for b in range(8))
        print(f'  |{line}|')

# Combinar base + nuevos (nuevos sobreescriben base)
todos = {**GLIFOS_BASE, **GLIFOS_NUEVOS}

data = bytearray(len(CHARS) * 16)

for char in CHARS:
    idx = CHARS.index(char)
    if char in todos:
        grid = make_8x8_from_5x5(todos[char])
        grid_rot = rotar_90_horario(grid)
        glyph = grid_to_glyph(grid_rot)
        data[idx*16:idx*16+16] = glyph
    # si no esta definido queda en ceros (invisible)

open(FUENTE_BIN, 'wb').write(data)
print(f'font_en.bin generada: {len(data)//16} glifos')

# Mostrar algunos para verificar
for c in GLIFOS_NUEVOS:
    mostrar_glifo(data, c)
