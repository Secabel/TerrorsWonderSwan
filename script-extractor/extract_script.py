"""
extract_script.py — Extractor estatico del guion completo de Terrors (WonderSwan)
Lee la ROM ORIGINAL japonesa (4MB) y la tabla de glifos (glyph_table.tsv).
Genera, por historia: todas las paginas en japones, con su cursor, entrada de la
tabla de punteros, preguntas/opciones y saltos (grafo de rutas).
"""
import sys, csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent            # E:\Descargas\Parche\Terrors\extractor_guion
ROM = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'Terrors (J) [M].ws'   # ROM ORIGINAL 4MB
TBL = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / 'glyph_table.tsv'
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE.parent / 'japanese-script'

STORIES = {"H1": (0x19, 0x30A0), "H2": (0x2A, 0), "H3": (0x18, 0),
           "H4": (0x33, 0), "H5": (0x29, 0), "H6": (0x38, 0)}

# bytes totales (incluye FF xx) que consume cada opcode, sacado del switch 0x341963
OPLEN = {0x00: 2, 0x01: 2, 0x02: 3, 0x03: 3, 0x05: 6, 0x07: 6, 0x08: 4, 0x0A: 3, 0x0B: 3,
         0x0C: 3, 0x0D: 7, 0x0E: 5, 0x0F: 3, 0x10: 3, 0x11: 2, 0x14: 2, 0x15: 2,
         0x3A: 10, 0x3B: 3, 0x3C: 4, 0x3D: 2, 0x3E: 2}
FONT_GLYPHS = 1727   # glifo >= esto no es texto (grafico)

rom = ROM.read_bytes()
tbl = {}
for line in TBL.read_text(encoding='utf-8').splitlines():
    if line and not line.startswith('#'):
        k, v = line.split('\t'); tbl[int(k, 16)] = v

def w(p): return rom[p] | (rom[p + 1] << 8)

def parse_story(name, bank, c92):
    base = bank * 0x10000 + c92
    n = w(base)
    # tabla de saltos: entrada t (BASE 0) -> cursor. Confirmado en 0x342541:
    # cursor = word[base + 2 + 2*t]  (sin restar 1)
    ptrs = [w(base + 2 + 2 * i) for i in range(n)]
    entry_at = {}
    for i, c in enumerate(ptrs): entry_at.setdefault(c, []).append(i)
    end = (bank + 1) * 0x10000 - base
    cur = (n + 1) * 2
    pages, page = [], None
    def new_page(c):
        return {'historia': name, 'cursor': c, 'entradas': [], 'texto': '', 'eventos': [],
                'glifos': 0, 'graf': 0, 'fin': None}
    page = new_page(cur)
    while cur < end - 1:
        if cur in entry_at and cur != page['cursor']:
            # una entrada de la tabla empieza aqui: es destino de salto -> pagina nueva
            if page['texto'].strip() or page['eventos']:
                page['fin'] = cur          # termina sin pausa (pregunta o salto): fin = inicio de la siguiente
                pages.append(page)
            page = new_page(cur)
        if cur in entry_at: page['entradas'] = entry_at[cur]
        p = base + cur; fb, sb = rom[p], rom[p + 1]
        if fb == 0xFF and sb & 0x80:
            op = sb & 0x7F; ln = OPLEN.get(op)
            if ln is None:
                page['eventos'].append(f'OP?{op:02X}'); ln = 2
            if op in (0, 1):
                page['fin'] = cur; pages.append(page); cur += 2
                page = new_page(cur)
                if cur in entry_at: page['entradas'] = entry_at[cur]
                continue
            if op == 0x3E: page['texto'] += '\n'
            elif op == 0x3B:
                page['texto'] += '\n'
                page['eventos'].append(f'PREGUNTA ({rom[p+2] & 0xF} opciones)')
            elif op == 0x3A:
                tgt = w(p + 8)
                dest = ptrs[tgt] if 0 <= tgt < n else None
                page['texto'] += f' ⇒[{tgt}]\n'
                page['eventos'].append(f'OPCION -> entrada {tgt} (cursor {dest:#06x})' if dest is not None
                                       else f'OPCION -> entrada {tgt} (?)')
            elif op == 0x3C:
                tgt = w(p + 2)
                dest = ptrs[tgt] if 0 <= tgt < n else None
                page['eventos'].append(f'SALTO -> entrada {tgt}' + (f' (cursor {dest:#06x})' if dest is not None else ''))
            elif op == 0x10:
                page['eventos'].append(f'SALTO_CONDICIONAL +{rom[p+2]} bytes')
            cur += ln
        else:
            if fb & 0x80: g = (fb & 0x7F) | ((sb & 0x7F) << 7); cur += 2
            else: g = fb; cur += 1
            page['glifos'] += 1
            if g >= FONT_GLYPHS: page['graf'] += 1; continue
            page['texto'] += tbl.get(g, f'⟨{g}⟩')
    return pages

def es_grafico(pg):
    # el motor de texto tambien dibuja imagenes: opcodes inexistentes, glifos fuera de la
    # fuente o paginas gigantes = datos graficos, no guion
    return (any(e.startswith('OP?') for e in pg['eventos']) or pg['glifos'] > 250
            or (pg['glifos'] and pg['graf'] / pg['glifos'] >= 0.1))

def es_texto(pg):
    return pg['glifos'] >= 1 and not es_grafico(pg)

if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    total = 0
    with open(OUT / 'full_script.csv', 'w', newline='', encoding='utf-8-sig') as fc:
        wr = csv.writer(fc, delimiter=';')
        wr.writerow(['historia', 'cursor', 'fin', 'entradas', 'eventos', 'texto'])
        for name, (bank, c92) in STORIES.items():
            pages = [pg for pg in parse_story(name, bank, c92) if not es_grafico(pg) and (es_texto(pg) or pg['eventos'])]
            with open(OUT / f'{name}.txt', 'w', encoding='utf-8') as ft:
                for pg in pages:
                    hdr = f"=== {name} cursor {pg['cursor']:#06x}"
                    if pg['entradas']: hdr += f"  [entrada {','.join(map(str, pg['entradas']))}]"
                    ft.write(hdr + '\n')
                    if es_texto(pg) and pg['texto'].strip(): ft.write(pg['texto'].strip() + '\n')
                    for e in pg['eventos']: ft.write('  >> ' + e + '\n')
                    ft.write('\n')
                    wr.writerow([name, f"{pg['cursor']:#06x}", f"{pg['fin']:#06x}" if pg['fin'] is not None else '',
                                 ','.join(map(str, pg['entradas'])), ' | '.join(pg['eventos']),
                                 pg['texto'].replace('\n', ' ').strip() if es_texto(pg) else ''])
            n = sum(1 for p in pages if es_texto(p)); total += n
            print(f'{name}: {n} paginas de texto')
    print('total', total)
