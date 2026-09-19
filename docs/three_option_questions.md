# Question screens with three options

The visual editor (`editor-visual/`) only supports the standard question screens (two numbered options plus a fixed context column). A few screens in the game show **three** numbered options plus the context text. Those rows must be packed **by hand** with the algorithm below.

Rows using this format in the CSVs (same screens in both languages): `H4;4`, `H4;103B`, `H4;103F`, `H3;87F`, `H5;58B`, `H5;191M`. You can recognise them because the `texto` field starts with `3.@`.

## How the row is stored in the CSV

- `tipo` = `texto` (**not** `pregunta`).
- `texto` = the packed string described below.
- The option columns (`opcion1_raw`, `opcion2_raw`, `opcion3_raw`) and the layout columns (`ancho_izq`, `esp_izq_centro`, ...) stay **empty**.
- `ty_offset` / `max_chars` describe the real width of each row of the packed block (see "Width" below). Usual values: `0` / `16`, or `1` / `15` when the screen has a graphic on the top row.

## The four columns

The question box is drawn as four vertical columns. From left to right on screen:

| Column | Content |
|---|---|
| 1 | Option 3 (starts with `3. `) |
| 2 | Option 2 (starts with `2. `) |
| 3 | Option 1 (starts with `1. `) |
| 4 | Context / dialogue text (no numeral) |

Each column has its own width `w` in characters (columns do not need the same width).

## Packing algorithm

1. **Word-wrap each column** to its width `w`, greedily: add words to the current line while `len(line) + 1 + len(word) <= w`; otherwise close the line and start a new one. A word longer than `w` is cut character by character into several lines (no hyphen or space is added at the cut).
2. **Pad every line** on the right with `@` up to `w + 1` characters. The extra character is a visual separator between columns. (`@` is the invisible-column-separator glyph.)
3. **Fix the number of rows at 15.** Columns with fewer lines are completed with empty lines (`w + 1` times `@`). A column that needs more than 15 lines does not fit; shorten the text.
4. **Build each row** by concatenating line *k* of column 1, 2, 3 and 4 (in that order).
5. **Join the 15 rows** into one string with a real space character (not `@`) between rows. No trailing space.

### Width

The four blocks must add up exactly to the width of the text box:

```
(w1 + 1) + (w2 + 1) + (w3 + 1) + (w4 + 1) = max_chars      and      max_chars = 16 - ty_offset
```

- `ty_offset = 0` -> `max_chars = 16` (default: four columns of width 3).
- `ty_offset = 1` -> `max_chars = 15` (screen with a graphic on the top row): one or more columns must be narrowed. There is no fixed rule for which one. Existing examples: `H3;87F` uses widths 3, 3, 2, 3 and `H4;103F` uses widths 2, 3, 2, 4. Columns can be narrowed and another widened, for example to avoid splitting a short word in the middle.

## Worked example (`H4;4`, widths 3, 3, 3, 3)

Columns (spanish text of the CSV):

| Col 1 | Col 2 | Col 3 | Col 4 |
|---|---|---|---|
| `3. TU VAS A SER MI FUTURA ESPOSA` | `2. QUIERO QUE LO CONOZCAS` | `1. ESTE... BUENO...` | `OYE, DE VERDAD ESTA BIEN QUE YO LO CONOZCA?` |

Wrapped to width 3, the first rows of each column are `3.`/`TU`/`VAS`/`A`/`SER`..., `2.`/`QUI`/`ERO`/`QUE`..., `1.`/`EST`/`E..`/`.`..., `OYE`/`,`/`DE`/`VER`/`DAD`... Row *k* of the output is line *k* of the four columns, each padded with `@` to 4 characters:

```
3.@@2.@@1.@@OYE@
TU@@QUI@EST@,@@@
VAS@ERO@E..@DE@@
A@@@QUE@.@@@VER@
...
```

These 15 rows joined with spaces are exactly the `texto` value of `H4;4`.

## Reference implementation

This function reproduces byte for byte the `texto` of `H4;4`, `H3;87F` and `H4;103F` from the CSV.

```python
def wrap(text, width):
    lines, cur = [], ""
    for word in text.split(" "):
        while len(word) > width:              # word longer than a full line: cut it
            if cur:
                lines.append(cur); cur = ""
            lines.append(word[:width]); word = word[width:]
        if not word:
            continue
        if cur == "":
            cur = word
        elif len(cur) + 1 + len(word) <= width:
            cur += " " + word
        else:
            lines.append(cur); cur = word
    if cur:
        lines.append(cur)
    return lines

def pack(columns, widths, rows=15):
    """columns = [option 3, option 2, option 1, context]; widths = [w1, w2, w3, w4]"""
    blocks = []
    for text, w in zip(columns, widths):
        lines = wrap(text, w)
        assert len(lines) <= rows, "column does not fit"
        lines += [""] * (rows - len(lines))
        blocks.append([l.ljust(w + 1, "@") for l in lines])
    return " ".join("".join(b[r] for b in blocks) for r in range(rows))
```

Example:

```python
pack(["3. TU VAS A SER MI FUTURA ESPOSA",
      "2. QUIERO QUE LO CONOZCAS",
      "1. ESTE... BUENO...",
      "OYE, DE VERDAD ESTA BIEN QUE YO LO CONOZCA?"], [3, 3, 3, 3])
```

## Tips

- After packing, check that `(w1+1)+(w2+1)+(w3+1)+(w4+1)` equals `max_chars`. If the text does not fit or a word is split badly, adjust the column widths and repack.
- Only ASCII characters are supported by the font (see the font files).
- Always test the result in an emulator: the number of rows and the real `ty_offset` of a screen can only be confirmed by looking at it.
