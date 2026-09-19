"""
generar_horizontal_compresion_eng_v21.py
Genera ROM traducida de Terrors WonderSwan (Rama B horizontal).

v21 (agosto 2026) -- FIX DEFINITIVO DEL LIBRO ANIMADO (elimina el destello
    del primer frame, permanente, sin freeze, sin romper la traduccion):
    reemplaza las DOS instrucciones "CALL 0x4451D" dentro de la rutina de
    animacion del libro (banco 0x34 offset local 0x1BF8 y 0x1C4C, mas
    espejo en banco 0x74) por NOP (0x90 0x90 0x90) -- 12 bytes en total.
    Esas dos llamadas son las UNICAS que efectivamente dibujan el icono
    del libro (una con el contador "viejo", otra con el contador
    "nuevo"/post-wrap); son exclusivas de esta rutina, no las usa nada
    mas del motor (el texto/kanji se dibuja por un camino de codigo
    completamente distinto). El resto de la rutina (contador, lectura de
    TABLA_LIBRO, calculo del wrap, es:[0x0C62]) queda intacto -- no se
    escribe ni se lee ninguna variable de RAM nueva.

    Mismo fix que generar_horizontal_compresion_v21.py (rama en espanol),
    aplicado aca porque esta rama comparte el mismo motor/direcciones --
    ver ese archivo para el detalle completo de la investigacion y de los
    3 enfoques descartados antes de llegar a este (parche de solo datos,
    forzar es:[0x09EA] desde el manejador de entrada, forzar es:[0x09EA]
    condicionado dentro de la rutina de animacion -- los tres fallaron
    por colisionar con variables de memoria compartidas con otros
    sistemas del motor, en particular con HOOKCAP/HOOKRES y con un
    mecanismo generico de cursor parpadeante).

    Validado en vivo (misma sesion, ROM en espanol) con corrida
    automatica completa de Historia 2 con creditos e Historia 5 con la
    ruta alterna P67-69 -- sin freeze, sin resto grafico del libro,
    traduccion intacta. Esta version en ingles aplica el mismo parche
    binario, en las mismas direcciones (confirmado identico a
    generar_horizontal_compresion_eng_v20.py salvo este cambio), pero
    NO se probo por separado en la ROM en ingles -- recomendado repetir
    al menos una corrida rapida antes de darlo por definitivo en esta
    rama.

v20 (agosto 2026) -- FIX GLOBAL DE SONIDO: elimina el glitch de audio
    intermitente ("pitidos", mas notorio en creditos pero reproducible en
    varios puntos del juego). Causa raiz encontrada con Mesen (ROM completa,
    breakpoint de lectura ROM en el rango fisico 0x430000-0x61FFFF, save de
    creditos H6): el motor original tiene 7 rutinas (en banco 0x34, mas sus
    7 espejos identicos en banco 0x74) que decodifican la envolvente de
    volumen de los canales de sonido leyendo datos directamente desde un
    banco de ROM seleccionado por el puerto $C2 (IO_BANK_ROM0) -- un
    mecanismo de bank-switch DISTINTO del puerto $C3 que usa el
    despachador/cave (ese ya tenia el FIX GLOBAL "and al,0x3F" de julio
    2026). El numero de banco sale directo del byte bajo de una celda de
    WRAM (es:[0x0BB2]/[0x0BB4]/[0x0BB6]/[0x0BB8]/[0x0BBA], segun el canal),
    SIN NINGUNA MASCARA: en la ROM original de 4MB (64 bancos, 6 bits) ese
    byte nunca podia superar 0x3F, pero con la ROM expandida a 8MB puede
    aterrizar en los bancos nuevos (0x43-0x61, donde vive la fuente/tablas
    de traduccion) y el motor manda esos bytes -- que no son datos de
    sonido -- directo al registro de volumen del canal (puerto $89,
    IO_SND_VOL_CH2), produciendo el pitido. Confirmado aislando el
    problema: poniendo en cero el contenido de esos bancos (con el cave
    neutralizado y sin ningun otro parche) el glitch desaparecia por
    completo; ese hallazgo llevo a buscar quien mas, aparte del cave, leia
    esos bancos.
    FIX (mismo enfoque que el FIX GLOBAL de julio 2026 para el puerto
    $C3): en vez de mover datos de banco (descartado explicitamente -- ya
    se habian validado ~300 rutas con la asignacion de bancos actual), se
    enmascara el byte con "AND AL,0x3F" justo antes de cada uno de los 14
    "OUT $C2,AL" (7 en banco 0x34 + 7 en banco 0x74), replicando el
    hardware original de 6 bits sin tocar ningun otro banco ni mecanismo
    compartido. Como estas 14 instrucciones son parte del motor original
    (no del cave inyectado) y no hay espacio libre junto a cada una para
    insertar la mascara in-line, se usa la tecnica de trampolin (igual
    estilo que los STUB1/STUBCAP/STUBRES del borrado de menu v19c): cada
    sitio se reemplaza por un JMP near de 3 bytes hacia un trampolin en la
    zona libre al final del banco (0xFEC0 en adelante, justo despues de
    donde terminan los stubs del borrado de menu -- sin colision); el
    trampolin re-ejecuta la carga de WRAM, aplica la mascara, hace el OUT,
    y vuelve. Validado en vivo por el usuario escuchando los creditos
    completos con la ROM parchada: "ya no se oyen los pitidos". Ver
    "CONTEXTO_GLITCH_SONIDO_2026-08-08_HANDOFF.md" para el detalle
    completo de la investigacion (incluye los caminos descartados:
    reentrancia de interrupciones, colisiones de escritura WRAM del cave,
    logica del cave, FIX PUNTUAL 1-5 y hooks de menu -- ninguno era la
    causa). Ver el bloque "FIX GLOBAL SONIDO" mas abajo (antes de escribir
    la ROM final) para el codigo exacto.
    Ademas, v20 revierte de v19e dos cambios de diagnostico que quedaron
    en el cave durante la investigacion del glitch (un CLI/STI alrededor
    del cambio de banco) -- se confirmo en vivo que NO tenian efecto sobre
    el glitch, asi que se sacan para dejar el cave igual que antes de
    empezar a investigar este bug.

v19d (julio 2026) -- FIX DE FREEZE: revierte el zereo de datos del libro
    animado (0x2CF000/0x6CF000) y el valor de TABLA_LIBRO a los de v19,
    porque esa combinacion (agregada en v19b/v19c) causaba un freeze
    reproducible en H5 (P67-69, ruta alterna) confirmado en vivo -- no
    relacionado con CSV ni bancos de datos (aislado probando CSV casi
    vacio y cambiando bancos, sin efecto en el freeze). Ver el comentario
    "REVERTIDO EN v19d" junto al zereo, mas abajo, para el detalle completo
    del diagnostico. Nada mas cambia respecto de v19c: mismo menu
    traducido (HOOKCAP/HOOKRES), mismo cave, mismos gates de 0x0069/0x0060,
    misma zona_chars multibanco, mismos bancos reservados.

v19c (julio 2026) -- MENU TRADUCIDO, mecanismo de borrado NUEVO y mas
    simple que v19/v19b, mas limpieza de codigo muerto que quedo obsoleto
    al cambiar de mecanismo:
    1) NUEVO mecanismo de borrado del menu (reemplaza TODO el mecanismo
       "HOOK1 escribe 0x0DB4 + cave lo lee" de v19/v19b, que fue abandonado
       por completo): HOOKCAP/HOOKRES (banco 0x34/0x74, offsets locales
       0x40FD/0x413E) ahora chequean DIRECTAMENTE, en el momento exacto
       del dibujado nativo, si es:[0x09D6]==0. Si es 0 (confirmado
       empiricamente: vale 0x0000 durante el menu, y toma un valor no-cero
       propio de cada historia -- 0x02F2..0x02F8 segun la tabla en banco
       0x34 offset 0x11C0 -- en cuanto se entra a jugar una) -> capturan/
       restauran igual que antes (borran el dibujado nativo, dejando ver
       el texto que el cave ya puso). Si es distinto de 0 -> no hacen nada,
       dejan pasar el dibujado nativo tal cual (la narrativa queda intacta).
       HOOK1 (offset local 0x3F84) pasa a ser un no-op puro: repite la
       instruccion original que reemplazo y vuelve, sin tocar RAM alguna --
       ya no hace falta que "avise" nada, porque HOOKCAP/HOOKRES ya no
       dependen de una bandera puesta por otro lado (0x0DB4). Esto elimina
       de raiz el problema de fondo de v19/v19b: el cave dispara con mucha
       menos frecuencia que la rutina de dibujado nativo, asi que cualquier
       bandera intermedia entre ambos quedaba expuesta a problemas de
       timing (se probaron variantes basadas en una lista fija de kanjis
       del menu, y en es:[0x09D4]/es:[0x09D6] leidos DESDE EL CAVE -- todas
       fallaban en activar el borrado por esta razon). Con el chequeo
       DENTRO de HOOKCAP/HOOKRES, en el mismo punto donde se dibuja, ese
       problema de timing deja de existir.
    2) LIMPIEZA -- se elimino el bloque MENU_PREV/MENU_CF del cave (v19,
       punto 3 mas abajo en el historial): dependia de que HOOK1 escribiera
       0x0DB4 para detectar el "flanco de entrada" al menu, algo que ya no
       pasa (HOOK1 es no-op ahora). Ese bloque habia quedado como codigo
       muerto (siempre tomaba la misma rama) con un riesgo lateral no
       probado: podia bloquear el redibujado del propio texto del cave en
       visitas repetidas al menu de 3/1 opciones. El kanji del menu ahora
       usa el mismo chequeo estandar de 0x0CF0 ("ya dibujado") que
       cualquier otra pantalla -- sin caso especial.
    3) LIMITACION CONOCIDA, sin resolver todavia: es:[0x09D6] se escribe
       en un UNICO lugar del juego (banco 0x34 local 0x13B0), que corre al
       ENTRAR a una historia -- nunca se resetea a 0 al volver a una
       pantalla de menu sin reiniciar el juego (por ejemplo via la opcion
       "insertar marcador" del menu de pausa, que muestra una pantalla de
       menu sin salir realmente de la historia activa). En ese caso
       puntual, es:[0x09D6] queda con el valor de la historia y el menu
       vuelve a mostrarse sin borrar el japones debajo. Probado en vivo:
       jugar H4, usar el marcador -> el japones reaparece en el menu.
       Pendiente: ubicar el codigo exacto que dispara esa pantalla de
       menu-via-marcador y forzar ahi un reset puntual de es:[0x09D6]=0.
    Historial de versiones anteriores (v19/v19b y previas), preservado
    para referencia -- el mecanismo que describen (HOOK1 escribe 0x0DB4,
    HOOKCAP/HOOKRES lo leen) YA NO ESTA ACTIVO en v19c, reemplazado por el
    punto 1 de arriba:

v19 (julio 2026) -- MENU TRADUCIDO, mecanismo completo (combina 3 piezas
    ya probadas + 2 fixes nuevos de esta version):
    1) Cave existente (es_kanji, sin cambios en su busqueda/dibujado) mas
       dos filas de CSV nuevas: pantalla 300 (kanji 0x03A, texto del menu
       de 3 opciones) y pantalla 301 (kanji 0x069, menu de 1 opcion).
    2) HOOK1/HOOKCAP/HOOKRES (banco 0x34/0x74, offsets locales 0x3F84/
       0x40FD/0x413E) -- capturan y restauran el contenido de VRAM en la
       rutina NATIVA de dibujado del menu, para que no vuelva a tapar el
       texto que el cave ya dibujo en cada refresco de pantalla. Sin
       cambios respecto de generar_horizontal_compresion_v18_menutest2.py
       -- documentado en detalle en HOOK_MENU_TRADUCCION.md.
    3) NUEVO en v19 -- flag de navegacion aislado (MENU_PREV/MENU_CF,
       WRAM 0x0DBC/0x0DBD): el flag global 0x0CF0 (que usa el cave para
       "ya dibuje esto, no repetir") depende de que el juego dispare el
       primer_kanji de OTRA fila para resetearse -- eso NUNCA pasa de
       forma confiable al volver atras y reentrar a la MISMA historia
       (confirmado jugando: cambiar de historia funcionaba, reentrar a
       la misma no). Se resuelve SOLO para las filas del menu (kanji
       0x03A/0x069, identificadas por valor fijo en el cave) usando el
       flag que ya escribe HOOK1 (0x0DB4, "esta linea es una de las 5
       reales del menu ahora mismo") para detectar el FLANCO de entrada
       (antes no estaba activo, ahora si) y resetear un flag PROPIO
       (MENU_CF), sin tocar 0x0CF0 -- el resto del dialogo del juego
       sigue exactamente igual que antes de este cambio.
    4) NUEVO en v19 -- fix de interferencia con el libro animado
       (ES_MENU_ACTUAL, WRAM 0x0DBE): el paso final del cave
       (.suprimir_libro) escribe sobre 0x0C7E, una variable REAL del
       motor (no nuestra) que tambien usa el fix del libro animado (v9).
       Ese paso se ejecuta al final de CUALQUIER dibujado exitoso,
       incluido el del menu -- y como el fix de arriba hace que el menu
       ahora si vuelva a dibujar en cada visita, tambien dispara este
       paso mas seguido, lo cual desincronizaba el estado del libro
       animado en la primera pantalla de la historia (basura grafica
       tapando el texto). Se agrega un flag (ES_MENU_ACTUAL) que marca
       si lo que se acaba de dibujar es el menu, y se saltea la
       escritura a 0x0C7E en ese caso -- el libro no aparece en el menu,
       asi que no hace falta tocar esa variable desde ahi.
    5) PROBADO pero DESACTIVADO en esta version -- zereo directo de los
       datos graficos originales del libro animado (0x2CF000/0x6CF000,
       ver TerrorsWonderSwan/docs/2026-06-27_libro_animado_solucion_v9.md
       para el freeze historico que causaba antes del redirect de
       TABLA_LIBRO). Se probo combinarlo con el redirect (que ya deja de
       leer esa zona, en teoria haciendo seguro el zereo) para eliminar
       los 1-2 frames de animacion visible que quedan antes de que el
       libro se vuelva invisible. Resultado en pruebas: aparicion
       intermitente de basura grafica en H5-P1, sin confirmar si el
       zereo es la causa real (no se pudo reproducir de forma
       consistente en pruebas repetidas). El bloque queda en el codigo
       (comentado, buscar "PRUEBA: zereo del libro animado") por si se
       retoma la investigacion -- el redirect de TABLA_LIBRO (v9, sin
       cambios) sigue activo y es lo que efectivamente esconde el libro
       en esta version.
    SI REAPARECE UN FREEZE relacionado al libro en el futuro: el primer
    sospechoso a revisar es reactivar el zereo del punto 5 (que esta
    desactivado en esta version, asi que no deberia ser la causa a menos
    que alguien lo reactive).

CONFIG DE BANCOS ACTUAL (julio 2026):
  BANCO_FUENTE       = 0x60  (fuente de tiles del alfabeto latino, reservado)
  BANCO_TABLA_INDICE = 0x40  (indice de pantallas, espejo de 0x00 -- unico
                               banco original que estaba todo 0xFF en la ROM
                               original, confirmado seguro por diagnostico)
  PRIMER_BANCO_DATOS = 0x43  (primer banco de datos de tiles)
  Bancos de datos en uso: 0x43, 0x44, 0x50, 0x51, 0x52, 0x53, 0x55, 0x41, 0x4B
  (0x41 pendiente de validacion completa; 0x4B paso pruebas criticas de H4/H5)

HALLAZGO CLAVE (julio 2026 -- pruebas de diagnostico_bancos.py):
  La ROM expandida es un espejo exacto de la ROM original de 4MB. El motor
  accede a bancos de la zona expandida (0x40-0x7F) por su propia logica,
  independientemente del cave. Esto significa que no existe un banco
  "libre" garantizado -- cada banco expandido puede ser usado por el motor
  en algun punto del juego. La unica excepcion confirmada es 0x40 (espejo
  de 0x00, que estaba todo 0xFF en la ROM original).

  Para identificar que banco causa un freeze especifico, usar
  diagnostico_bancos.py: escribe 0xFF en cada banco sospechoso sobre la
  ROM espejo pura (sin cave ni parche) y reproduce el freeze. Si ocurre
  igual, el motor lee ese banco por su cuenta -- descartado. Si no ocurre,
  el problema es lo que escribimos ahi.

IMPORTANTE (julio 2026): se confirmo que la seguridad de un banco puede
ser especifica a una PANTALLA puntual, no a una historia completa.

v17 (julio 2026): dos mejoras de seguridad al proceso, sin cambiar la
    logica de generacion en si:
    1) Validacion previa de caracteres invalidos: lista TODAS las pantallas
       afectadas con el caracter especifico, no solo la primera.
    2) BANCO_TABLA_INDICE y BANCO_FUENTE ahora se validan contra
       BANCOS_PROHIBIDOS igual que PRIMER_BANCO_DATOS.
    3) 0x74 agregado a BANCOS_RESERVADOS (parches del fix del libro).
v16 (julio 2026): investigacion de BANCO_TABLA_INDICE. Se probaron
    candidatos 0x61, 0x65, 0x68, 0x69, 0x71, 0x70 -- todos fallaron.
    Distincion de mecanismo: hay DOS categorias de freeze:
    (1) Overflow de PRIMER_BANCO_DATOS (depende del volumen de texto).
    (2) Identidad de BANCO_TABLA_INDICE (depende del banco especifico).
v15 (julio 2026): agrega 0x45, 0x46, 0x48, 0x49, 0x4A, 0x4B, 0x4C a
    BANCOS_PROHIBIDOS -- confirmados en H4 fase de captura.
    NOTA: 0x4B fue revalidado con diagnostico_bancos.py en julio 2026 y
    paso las pruebas criticas (H4-P163, H4-P218, H5-P262) -- removido de
    la lista negra. Ver comentario en BANCOS_PROHIBIDOS.
v14: agrega BANCOS_PROHIBIDOS + siguiente_banco_datos().
v9: fix del libro animado (tabla propia de 3 bytes en 0x34F992).
v8: soporte multi-historia (10 bytes/entrada en pant_tabla, historia en
    RAM 0x09D8).
v5: pant_tabla movida a banco propio.
"""

import csv
import io
import os
import re
import subprocess
import sys

ROM_INPUT = 'Terrors_expanded.ws'
ROM_OUTPUT = 'Terrors_EN.ws'
FUENTE_BIN = 'font/font_en.bin'
CSV_INPUT = 'data/translation_en.csv'
CAVE_ASM = 'src/cave_en.asm'
CAVE_BIN = 'src/cave_en.bin'

CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ.,?!-1234567890@:'"

def word_wrap(texto, max_cols):
    palabras = texto.upper().split()
    fragmentos = []
    for p in palabras:
        while len(p) > max_cols:
            fragmentos.append(p[:max_cols])
            p = p[max_cols:]
        fragmentos.append(p)
    cols, col = [], ''
    for p in fragmentos:
        if not col:
            col = p
        elif len(col) + 1 + len(p) <= max_cols:
            col += ' ' + p
        else:
            cols.append(col)
            col = p
    if col:
        cols.append(col)
    return cols

def make_tile_tabla(texto, ty_offset, max_chars):
    cols = word_wrap(texto, max_chars)
    tabla = []
    for col_idx, col in enumerate(cols):
        tx = 15 - col_idx
        if tx < 0:
            break
        for ty_idx, c in enumerate(col):
            if c not in CHARS:
                # No debería llegar aca nunca: la validacion previa ya
                # revisa todas las pantallas antes de generar nada. Si
                # esto dispara, es un caracter que se coló de otra forma
                # (ej. agregado en tiempo de ejecucion) -- se deja como
                # ultima red de seguridad, no como mecanismo principal.
                print(f'ERROR INESPERADO: caracter {repr(c)} no existe en la fuente '
                      f'(esto no deberia pasar, la validacion previa deberia haberlo atrapado)')
                sys.exit(1)
            tile_index = 0x100 + (ty_idx + ty_offset) * 0x10 + tx
            tileset_addr = 0x2000 + tile_index * 16
            if tileset_addr > 0x3FF0:
                break
            char_idx = CHARS.index(c)
            tabla.append((tileset_addr, char_idx))
    return tabla


# Flag para pantallas con formato comprimido (bit 15 del count en pant_tabla)
FLAG_COMPRIMIDO = 0x8000

def make_zona_B_entry(texto, ty_offset, max_chars, zona_chars_index, zona_chars):
    """Para una pantalla, genera:
    - zona_B: lista de (tileset_addr_base, char_bank_idx, char_offset, word_len)
      char_bank_idx es un indice RELATIVO (0, 1, 2...) de banco dentro de la
      zona_chars global -- 0 es el primer banco de zona_chars (PRIMER_BANCO_DATOS),
      1 el siguiente banco que haya hecho falta para el desborde, etc. Se
      traduce a numero de banco real recien en la pasada de escritura a ROM,
      una vez que se sabe que bancos reales le tocaron a cada indice.
    - Actualiza zona_chars con palabras nuevas (deduplicado por contenido)

    zona_chars ya no esta limitada a un solo banco de 64KB: si no entra mas
    en el banco actual, se sigue escribiendo en el siguiente (igual mecanismo
    que zona_B ya usaba para desbordar pantallas entre bancos). La unica
    restriccion es que una misma palabra nunca puede quedar partida entre
    dos bancos (el cave banca-switchea una sola vez por palabra, no por
    caracter) -- si una palabra nueva no entra completa en el banco actual,
    se rellena el resto del banco con ceros (padding, nunca referenciado)
    y la palabra arranca limpia al principio del siguiente banco.
    """
    cols = word_wrap(texto, max_chars)
    zona_B = []
    for col_idx, col in enumerate(cols):
        tx = 15 - col_idx
        if tx < 0:
            break
        partes = col.split(' ')
        ty_actual = 0
        for parte_idx, parte in enumerate(partes):
            if parte_idx > 0:
                ty_actual += 1
            # tileset_addr_base = primera letra de la palabra
            tile_index = 0x100 + (ty_actual + ty_offset) * 0x10 + tx
            tileset_addr_base = 0x2000 + tile_index * 16
            if tileset_addr_base > 0x3FF0:
                break
            # Registrar palabra en zona_chars si no existe
            if parte not in zona_chars_index:
                # No dejar que la palabra cruce un limite de banco (64KB):
                # si no entra completa en el banco actual, rellenar hasta
                # el limite antes de empezar a escribirla.
                offset_en_banco = len(zona_chars) % 0x10000
                if offset_en_banco + len(parte) > 0x10000:
                    relleno = 0x10000 - offset_en_banco
                    zona_chars.extend([0] * relleno)
                zona_chars_index[parte] = len(zona_chars)
                for c in parte:
                    if c not in CHARS:
                        print(f'ERROR INESPERADO: caracter {repr(c)} no existe en la fuente')
                        sys.exit(1)
                    zona_chars.append(CHARS.index(c))
            char_offset_global = zona_chars_index[parte]
            char_bank_idx = char_offset_global // 0x10000
            char_offset = char_offset_global % 0x10000
            zona_B.append((tileset_addr_base, char_bank_idx, char_offset, len(parte)))
            ty_actual += len(parte)
    return zona_B

def hex_int(s):
    s = s.strip()
    return int(s, 16)

def historia_a_indice(s):
    """Convierte 'H1'..'H6' al indice base-0 usado por el motor (0x09D8: 0=H1...5=H6).
    Tambien acepta 'H1B'..'H5B' -- pseudo-historias usadas SOLO por la
    variante de 2 opciones del kanji 0x0069 (ver FIX v20 en el cave: dh se
    ajusta +0x10 en vivo cuando es:[0x0A2A]==1). Se mapean a 0x10..0x14,
    nunca colisionan con H1..H6 (0..5).
    Tambien acepta 'H1C'..'H5C' -- pseudo-historias usadas SOLO por la
    variante "reiniciar esta historia" del kanji 0x0060 (ver FIX v20 en
    el cave: dh se ajusta +0x20 en vivo cuando es:[0x09E6]==1). Se mapean
    a 0x20..0x24, nunca colisionan con H1..H6 ni con H1B..H5B.
    Lanza ValueError si el valor no matchea (el llamador decide como reportarlo)."""
    s = s.strip().upper()
    m = re.match(r'^H([1-5])B$', s)
    if m:
        return 0x10 + int(m.group(1)) - 1
    m = re.match(r'^H([1-5])C$', s)
    if m:
        return 0x20 + int(m.group(1)) - 1
    m = re.match(r'^H([1-6])$', s)
    if not m:
        raise ValueError(f"valor de 'historia' invalido: {repr(s)} (debe ser H1..H6, H1B..H5B o H1C..H5C)")
    return int(m.group(1)) - 1

def sort_key(k):
    """Acepta tanto una clave compuesta (hist_idx, pantalla) como un string
    de pantalla suelto (compatibilidad). Ordena primero por historia, luego
    por numero de pantalla, luego por sufijo (ej. '7B' despues de '7')."""
    if isinstance(k, tuple):
        hist_idx, p = k
    else:
        hist_idx, p = 0, k
    m = re.match(r'^(\d+)(.*)$', str(p))
    p_key = (int(m.group(1)), m.group(2)) if m else (0, str(p))
    return (hist_idx,) + p_key

# ----------------------------------------------------------------------
# Leer CSV
#
# NOTA (julio 2026): antes, un solo campo mal cargado (ej. ultimo_kanji
# vacio) hacia crashear el script entero con un traceback que solo
# apuntaba a la linea del CODIGO (siempre la misma), sin decir en que
# FILA del CSV ni en que pantalla estaba el dato malo -- forzaba a
# adivinar. Ahora se valida fila por fila, se juntan TODOS los errores
# (no solo el primero) y se listan con historia+pantalla+numero de linea
# de CSV antes de abortar, igual que las otras validaciones de mas abajo.
# ----------------------------------------------------------------------
def parse_int_campo(valor, nombre_campo, base=10):
    """Convierte un campo numerico, devolviendo (ok, valor_o_None)."""
    v = valor.strip() if isinstance(valor, str) else valor
    if not v:
        return False, None
    try:
        return True, int(v, base) if base == 16 else int(v)
    except ValueError:
        return False, None

pantallas = {}
errores_csv = []
# Se lee en binario primero y se decodifica a mano (en vez de open(...,
# encoding=...) directo) por dos motivos:
#  1) El CSV puede tener bytes NUL sueltos (tipico de herramientas que
#     dejan padding binario al final del archivo) -- el modulo csv se
#     niega a parsear CUALQUIER archivo con un solo NUL, con un error que
#     no menciona fila ni pantalla ("line contains NUL"). Se filtran aca.
#  2) El CSV puede tener bytes que no son UTF-8 valido (tipico de texto
#     pegado desde Word/Excel con caracteres especiales -- comillas
#     curvas, puntos suspensivos "...", tildes mal copiadas -- guardados
#     en Windows-1252 en vez de UTF-8). Si el archivo no decodifica como
#     UTF-8, se reintenta con cp1252 (superset de Latin-1, la codificacion
#     mas probable en Windows) y se avisa la posicion aproximada para que
#     se pueda revisar y limpiar esa fila si el texto sale con caracteres
#     raros.
_csv_bytes = open(CSV_INPUT, 'rb').read()
if _csv_bytes.startswith(b'\xef\xbb\xbf'):
    _csv_bytes = _csv_bytes[3:]  # BOM utf-8-sig
try:
    contenido = _csv_bytes.decode('utf-8')
except UnicodeDecodeError as _e:
    _linea_aprox = _csv_bytes[:_e.start].count(b'\n') + 1
    print(f"ADVERTENCIA: el CSV tiene un byte invalido para UTF-8 en la posicion "
          f"{_e.start} (cerca de la linea {_linea_aprox}, byte {_csv_bytes[_e.start]:#04x}). "
          f"Probablemente un caracter especial pegado desde Word/Excel con otra "
          f"codificacion. Se decodifica como cp1252 (Windows) de resguardo -- revisa "
          f"esa linea en el CSV si algun texto sale con caracteres raros.")
    contenido = _csv_bytes.decode('cp1252')
contenido = contenido.replace('\x00', '')
with io.StringIO(contenido) as f:
    reader = csv.DictReader(f, delimiter=';')
    needed = {'historia', 'pantalla', 'texto', 'ty_offset', 'max_chars', 'primer_kanji', 'ultimo_kanji'}
    if not needed.issubset(reader.fieldnames):
        print(f"ERROR: El CSV debe tener columnas: {needed}")
        sys.exit(1)
    # line_num arranca en 1 (header); la primera fila de datos es la 2,
    # igual que se ve al abrir el CSV en un editor de texto/Excel.
    for row in reader:
        line_num = reader.line_num
        etiqueta_cruda = f"H{row.get('historia','?').strip()}-P{row.get('pantalla','?').strip()} (linea CSV {line_num})"

        ok_hist = True
        try:
            hist_idx = historia_a_indice(row['historia'])
        except ValueError as e:
            errores_csv.append(f"{etiqueta_cruda}: columna 'historia' invalida: {row.get('historia')!r} ({e})")
            ok_hist = False
            hist_idx = None

        ok_ty, ty_offset = parse_int_campo(row.get('ty_offset', ''), 'ty_offset')
        if not ok_ty:
            errores_csv.append(f"{etiqueta_cruda}: columna 'ty_offset' vacia o invalida: {row.get('ty_offset')!r}")

        ok_max, max_chars = parse_int_campo(row.get('max_chars', ''), 'max_chars')
        if not ok_max:
            errores_csv.append(f"{etiqueta_cruda}: columna 'max_chars' vacia o invalida: {row.get('max_chars')!r}")

        ok_prim, primer_kanji = parse_int_campo(row.get('primer_kanji', ''), 'primer_kanji', base=16)
        if not ok_prim:
            errores_csv.append(f"{etiqueta_cruda}: columna 'primer_kanji' vacia o invalida (se esperaba hex, ej. 0x1234): {row.get('primer_kanji')!r}")

        ok_ult, ultimo_kanji = parse_int_campo(row.get('ultimo_kanji', ''), 'ultimo_kanji', base=16)
        if not ok_ult:
            errores_csv.append(f"{etiqueta_cruda}: columna 'ultimo_kanji' vacia o invalida (se esperaba hex, ej. 0x1234): {row.get('ultimo_kanji')!r}")

        # ruta_ref (v19e, campo NUEVO y DEDICADO, 12 bytes/entrada en
        # pant_tabla): opcional. Si esta vacio, se usa el centinela 0xFFFF
        # (== "esta fila no participa de la logica de desambiguacion de
        # ruta, PASE1 la ignora"). Si tiene un valor, PASE1 lo compara
        # contra ULTIMA_PANTALLA_UK para decidir si ESTA fila especifica
        # es la que corresponde a la ruta actual. A diferencia del intento
        # anterior, este campo NUNCA se confunde con 'primer_kanji' (que
        # ahora vuelve a ser 100% el primer_kanji real, usado por PASE2
        # para el reset de 0x0CF0 como siempre).
        _ruta_ref_raw = row.get('ruta_ref', '').strip() if row.get('ruta_ref') else ''
        if _ruta_ref_raw:
            ok_ruta_ref, ruta_ref = parse_int_campo(_ruta_ref_raw, 'ruta_ref', base=16)
            if not ok_ruta_ref:
                errores_csv.append(f"{etiqueta_cruda}: columna 'ruta_ref' invalida (se esperaba hex, ej. 0x1234, o vacio): {row.get('ruta_ref')!r}")
        else:
            ok_ruta_ref, ruta_ref = True, 0xFFFF

        # produce_marca / espera_marca (v19e, segundo mecanismo de
        # desambiguacion, para cuando DOS filas duplicadas (ej. version
        # larga/corta de una misma pantalla compartida) ya dejaron el MISMO
        # ultimo_kanji en ULTIMA_PANTALLA_UK, y una tercera fila necesita
        # saber CUAL de esas dos se dibujo -- ruta_ref/ULTIMA_PANTALLA_UK ya
        # no alcanza porque ambas producen el mismo valor real de kanji.
        # produce_marca: numero inventado (1, 2, ...) que ESTA fila anota en
        # ULTIMA_MARCA_RUTA (WRAM aparte, nunca comparada contra kanjis
        # reales) al dibujarse -- no puede chocar con nada real porque no es
        # un kanji, es un identificador puramente nuestro.
        # espera_marca: el valor que esta fila exige encontrar en
        # ULTIMA_MARCA_RUTA para ser elegida (PASE 1B, ver ASM).
        # Sentinel 0xFF = "no participa" en ambos casos.
        _prod_raw = row.get('produce_marca', '').strip() if row.get('produce_marca') else ''
        if _prod_raw:
            ok_prod, produce_marca = parse_int_campo(_prod_raw, 'produce_marca', base=10)
            if not ok_prod:
                errores_csv.append(f"{etiqueta_cruda}: columna 'produce_marca' invalida (se esperaba un numero, ej. 1, o vacio): {row.get('produce_marca')!r}")
        else:
            ok_prod, produce_marca = True, 0xFF

        _esp_raw = row.get('espera_marca', '').strip() if row.get('espera_marca') else ''
        if _esp_raw:
            ok_esp, espera_marca = parse_int_campo(_esp_raw, 'espera_marca', base=10)
            if not ok_esp:
                errores_csv.append(f"{etiqueta_cruda}: columna 'espera_marca' invalida (se esperaba un numero, ej. 1, o vacio): {row.get('espera_marca')!r}")
        else:
            ok_esp, espera_marca = True, 0xFF

        if not (ok_hist and ok_ty and ok_max and ok_prim and ok_ult and ok_ruta_ref and ok_prod and ok_esp):
            continue  # ya quedo registrado el error; no seguir armando esta fila

        p = row['pantalla'].strip()
        # Clave compuesta: una misma pantalla (ej. P1) puede existir en
        # mas de una historia (P1-H1 y P1-H3 son entradas distintas).
        clave = (hist_idx, p)
        # Nota: la columna 'tipo' (texto/pregunta) es solo informativa para
        # identificar visualmente las pantallas de pregunta en el CSV.
        # El generador trata todas las pantallas igual, sin importar su tipo:
        # las pantallas de pregunta ya vienen con el texto preformateado
        # (fragmentos de 4 caracteres + @ invisible) desde el editor visual.
        pantallas[clave] = {
            'historia': hist_idx,
            'historia_nombre': row['historia'].strip().upper(),
            'pantalla': p,
            'texto': row['texto'],
            'ty_offset': ty_offset,
            'max_chars': max_chars,
            'primer_kanji': primer_kanji,
            'ultimo_kanji': ultimo_kanji,
            'ruta_ref': ruta_ref,
            'produce_marca': produce_marca,
            'espera_marca': espera_marca,
        }

if errores_csv:
    print(f"\n=== CSV INVALIDO: {len(errores_csv)} fila(s) con problemas -- no se genero ninguna ROM ===")
    for e in errores_csv:
        print(f"  - {e}")
    print("\nCorregi esas filas en el CSV (completar el campo vacio, o borrar la fila si no corresponde) y volve a correr el script.")
    sys.exit(1)

if not pantallas:
    print("No hay pantallas validas en el CSV.")
    sys.exit(1)

n_pant = len(pantallas)
print(f'Pantallas activas: {sorted(pantallas.keys(), key=sort_key)}')

# ----------------------------------------------------------------------
# Validacion de configuracion de bancos fijos (NUEVO en v17)
# Antes solo se chequeaba PRIMER_BANCO_DATOS contra la lista negra. Un
# banco confirmado como problematico en un contexto (ej. como banco de
# datos) tiene alta probabilidad de serlo tambien en otro rol (indice o
# fuente) -- mejor abortar temprano con un error claro que descubrirlo
# jugando horas despues.
# (Esta validacion vive antes de BANCOS_PROHIBIDOS mas abajo por claridad
# de lectura, pero en el codigo real se ejecuta despues de definir esas
# constantes -- ver bloque "Construir datos de tiles" mas abajo.)
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Validaciones previas (solo alertan y rechazan, no corrigen nada)
# ----------------------------------------------------------------------
errores_validacion = []

# 1. Campo 'texto' vacio -> ya confirmado que cuelga el cave en juego real
for clave in sorted(pantallas, key=sort_key):
    d = pantallas[clave]
    if not d['texto'].strip():
        errores_validacion.append(
            f"{d['historia_nombre']}-P{d['pantalla']}: campo 'texto' esta vacio (esto congela el juego)")

# 2. Colision de ultimo_kanji entre pantallas de la MISMA historia
# COLISION ULTIMO_KANJI COMENTADA para pruebas con dummy
#vistos_ultimo = {}
#for clave in sorted(pantallas, key=sort_key):
#    d = pantallas[clave]
#    uk = d['ultimo_kanji']
#    clave_colision = (d['historia'], uk)
#    if clave_colision in vistos_ultimo:
#        errores_validacion.append(
#            f"{d['historia_nombre']}-P{d['pantalla']}: ultimo_kanji=0x{uk:04X} colisiona con "
#            f"{d['historia_nombre']}-P{vistos_ultimo[clave_colision]} "
#            f"(el cave nunca llegara a una de las dos)")
#    else:
#        vistos_ultimo[clave_colision] = d['pantalla']

# 3. Caracteres invalidos (NUEVO en v17) -- antes esto se detectaba recien
# dentro de make_tile_tabla, abortando con sys.exit() sin decir en que
# pantalla, forzando a revisar el CSV entero a mano para encontrarlo.
# Ahora se escanea TODO el CSV de una pasada y se listan TODAS las
# pantallas con caracteres invalidos, con el/los caracter(es) especificos.
for clave in sorted(pantallas, key=sort_key):
    d = pantallas[clave]
    invalidos = sorted(set(c for c in d['texto'].upper() if c not in CHARS))
    if invalidos:
        errores_validacion.append(
            f"{d['historia_nombre']}-P{d['pantalla']}: caracter(es) invalido(s) {invalidos} "
            f"no existen en la fuente (charset permitido: {repr(CHARS)})")

if errores_validacion:
    print("\n=== VALIDACION FALLIDA: no se genero ninguna ROM ===")
    for e in errores_validacion:
        print(f"  - {e}")
    print(f"\nTotal errores: {len(errores_validacion)}")
    sys.exit(1)

print("Validaciones previas: OK (sin texto vacio, sin colisiones de ultimo_kanji, sin caracteres invalidos)")

# ----------------------------------------------------------------------
# Construir datos de tiles en multiples bancos, empezando en
# PRIMER_BANCO_DATOS (0x43) y saltando a los siguientes bancos validos via
# siguiente_banco_datos() si hace falta overflow (ver BANCOS_PROHIBIDOS).
# pant_tabla vive sola en el banco BANCO_TABLA_INDICE (0x40), 10 bytes/entrada.
# Layout banco BANCO_TABLA_INDICE (0x40):
#   [0x0000 .. n_pant*10-1] : pant_tabla (10 bytes por entrada)
# Layout de cada banco de datos (0x43, 0x44, 0x50... saltando prohibidos):
#   [0x0000 ..] : datos de tiles de las pantallas asignadas a ese banco
# ----------------------------------------------------------------------
BANCO_TABLA_INDICE = 0x40
BANCO_FUENTE = 0x60
PRIMER_BANCO_DATOS = 0x43

# v22 (optimizacion de busqueda del cave, misma logica que la rama en
# espanol -- ver generar_horizontal_compresion_opt_v22.py): banco NUEVO,
# exclusivo para las tablas auxiliares de busqueda (TABLA_A, TABLA_B). NO
# reemplaza ni reordena pant_tabla (sigue igual: mismo banco
# BANCO_TABLA_INDICE, mismo formato, mismo orden) -- las tablas nuevas
# solo apuntan a ella por offset de bytes.
# *** BANCO SIN PROBAR EN VIVO EN ESTA RAMA (INGLES) ***: se verifico que
# BANCOS_PROHIBIDOS es identico entre esta rama y la rama en espanol (o
# sea 0x41 no esta en la lista negra tampoco aca), y la rama en espanol ya
# probo este banco en vivo sin freeze durante un capitulo completo -- pero
# no reemplaza probarlo tambien en la ROM en ingles antes de confiar del
# todo.
BANCO_TABLA_OPT = 0x41

# Bancos que NO se pueden usar para datos de traduccion, por dos motivos:
#  1) Estan en la tabla del motor 0xFF370 (18 bancos reales que el juego
#     banquea directamente para sus propios datos/audio) -> confirmado por
#     analisis del ROM original, no probado uno por uno en juego.
#  2) Confirmados EMPIRICAMENTE como causantes de freeze al probarlos en
#     Mesen/hardware, aunque no aparecian en la tabla del motor (el
#     mecanismo exacto sigue sin confirmarse del todo).
BANCOS_PROHIBIDOS = {
    0x4B,  # 4B graficos corruptos en H4B P83, P88 y freeze en P89 
    # -- tabla 0xFF370 (uso directo del motor, confirmado por analisis
    #    estatico del ROM original, no probado uno por uno en juego) --
    0x47, 0x4D, 0x4E, 0x4F, 0x54, 0x56, 0x67, 0x6D, 0x6E, 0x6F,
    0x72, 0x75, 0x77, 0x78, 0x7A, 0x7C, 0x7D, 0x7F,
    # -- confirmados empiricamente jugando en Mesen, julio 2026 --
    0x42,  # BANCO_TABLA_INDICE viejo -> freeze reproducible en H3-P206
    0x62,  # PRIMER_BANCO_DATOS candidato -> freeze en pantalla principal/menu
    0x45,  # freeze en H4-P218 (creditos H4)
    0x46,  # reinicio en H4B-P163
    0x48,  # reinicio en H4-P163
    0x49,  # reinicio en H4-P163
    0x4A,  # reinicio en H4-P163
    0x4C,  # reinicio en H4-P163
    # NOTA: 0x4B fue parte de este grupo pero paso las pruebas de diagnostico
    # (H4-P163, H4-P218, H5-P262) -- se deja como banco de datos valido.
    # Si genera freeze, aislar con diagnostico_bancos.py y reportar pantalla exacta.
    # -- candidatos de BANCO_TABLA_INDICE descartados (julio 2026) --
    #0x61,  # freeze en H5-P19
    0x63,  # freeze en H5-P87/88
    0x64,  # reinicio inmediato en H5
    0x65,  # rompe el selector de historias al ciclar entre ellas en el menu
    0x66,  # freeze en H5-P66 (borra libro animado)
    0x68,  # freeze en H5 ruta alterna P67
    0x69,  # freeze en H5 ruta alterna
    0x6A,  # freeze en H5-P66 (mismo sintoma que 0x66/0x6C)
    0x6B,  # congela el juego al inicio
    0x6C,  # libro blanco + freeze en H5-P66
    0x70,  # paso H5 completa pero fallo H4-P78/79 (ambiguo, nunca aislado del todo)
    0x71,  # freeze en H5 ruta alterna P65, reproducido con save
    0x73,  # congela H4 al inicio
    0x76,  # reinicia H5 al inicio
    0x79,  # error en menu (contexto exacto sin detallar del todo)
    0x7B,  # reinicia el juego en el menu
    0x7E,  # borra los kanjis del juego original
    # -- descartados por prueba de diagnostico_bancos.py (julio 2026) --
    # Probados escribiendo 0xFF en el banco completo sobre la ROM espejo pura.
    # Descarte 100% confirmado: el motor lee esos bancos por su cuenta,
    # independientemente del cave o los datos del parche.
#    0x58,  # (ex-prohibido) congelaba H3 al inicio -- CONFIRMADO 2026-08:
           # el mismo mecanismo de entrada de tabla corrupta que ya
           # arreglaban FIX PUNTUAL 3/4/5 (byte corrupto en la tabla de
           # bancos del motor que, enmascarado, caia en este banco). Se
           # habilito, se lleno completo con datos reales del cave (bloque
           # de 420 dummies, ver seccion de pruebas), y el usuario confirmo
           # en vivo (Mesen) que H1C y H3 arrancan sin freeze. Banco de
           # datos valido desde esta fecha.
#    0x59,  # (ex-prohibido) congelaba H1 al inicio -- CONFIRMADO 2026-08,
           # misma prueba y mismo resultado que 0x58 (ver arriba). Banco
           # de datos valido desde esta fecha.
    0x5A,  # congela el menu
    0x5B,  # freeze en H5-P55
    0x5C,  # freeze en H5-P163
    0x5D,  # freeze en H5-P262/263
    0x5E,  # freeze en H3-P2 (inicio)
    0x5F,  # freeze en H5-P87
#    0x50,  # freeze P149-H1 (corregido)
#    0x51,  # freeze P184-H1C

}
# Bancos ya reservados para otros fines (no deben reutilizarse para datos
# aunque no esten en la lista negra de arriba)
BANCOS_RESERVADOS = {BANCO_FUENTE, BANCO_TABLA_INDICE, BANCO_TABLA_OPT, 0x4F, 0x74}
# 0x4F = banco del cave (0x34F802/0x74F802)
# 0x74 = espejo de 0x34, donde viven los parches del fix del libro:
#        tabla en 0x34F992/0x74F992, punteros redirigidos en
#        0x34172D/0x341757 y sus espejos 0x74172D/0x741757. Escribir
#        pant_tabla o cualquier dato ahi se pisa a si mismo con estos
#        parches ya existentes -- descubierto por el assert de
#        verificacion de bytes originales (colision 100% determinista,
#        NO relacionada al tipo de freeze "el motor usa este banco en
#        algun momento" -- esta se puede calcular sin jugar nada).

# Validacion de los TRES bancos fijos: contra la lista negra (bancos
# confirmados problematicos jugando) Y contra los internos siempre
# reservados (0x4F cave, 0x74 parches del libro) -- NUEVO en v17. Antes
# solo se chequeaba PRIMER_BANCO_DATOS contra la lista negra, y nada
# validaba 0x74 en absoluto (por eso la colision de recien llego hasta el
# assert en vez de detectarse aca, temprano y con mensaje claro).
_FIJOS_INTERNOS = {0x4F, 0x74}
_bancos_fijos = {
    'BANCO_TABLA_INDICE': BANCO_TABLA_INDICE,
    'BANCO_FUENTE': BANCO_FUENTE,
    'PRIMER_BANCO_DATOS': PRIMER_BANCO_DATOS,
    'BANCO_TABLA_OPT': BANCO_TABLA_OPT,
}
_errores_config = []
for _nombre, _banco in _bancos_fijos.items():
    if _banco in BANCOS_PROHIBIDOS:
        _errores_config.append(
            f"{_nombre}=0x{_banco:02X} esta en BANCOS_PROHIBIDOS (confirmado problematico "
            f"anteriormente). No se genera la ROM -- elegir otro banco.")
    if _banco in _FIJOS_INTERNOS:
        _errores_config.append(
            f"{_nombre}=0x{_banco:02X} esta reservado internamente (cave en 0x4F, "
            f"parches del fix del libro en 0x74) -- elegir otro banco.")
if _errores_config:
    print("\n=== CONFIGURACION INVALIDA: no se genero ninguna ROM ===")
    for e in _errores_config:
        print(f"  - {e}")
    sys.exit(1)

def siguiente_banco_datos(banco_actual):
    """Devuelve el siguiente banco de datos valido despues de banco_actual,
    saltando automaticamente cualquier banco prohibido o reservado."""
    candidato = banco_actual + 1
    while candidato in BANCOS_PROHIBIDOS or candidato in BANCOS_RESERVADOS:
        print(f'  (banco 0x{candidato:02X} esta en la lista negra/reservados, se salta)')
        candidato += 1
        if candidato > 0x7F:
            print('ERROR: se agotaron los bancos disponibles (0x00-0x7F) sin encontrar uno valido')
            sys.exit(1)
    return candidato

# bancos_datos[i] = bytearray del banco bancos_reales[i]
bancos_datos = [bytearray(0x10000)]
bancos_reales = [PRIMER_BANCO_DATOS]  # numero de banco real correspondiente a cada indice
banco_actual_idx = 0
pos = 0  # posicion dentro del banco actual

offsets = {}   # clave -> offset dentro de su banco
counts = {}    # clave -> cantidad de entradas
bancos_de_pantalla = {}  # clave -> numero de banco real (bancos_reales[idx])

# --- PASADA 1: construir zona_chars global y zona_B por pantalla ---
# zona_chars: lista de char_idx, deduplicada por contenido de palabra
# zona_B[clave]: lista de (tileset_addr_base, char_offset, word_len)
zona_chars = []          # char_idx por palabra unica (1 byte c/u)
zona_chars_index = {}    # palabra -> offset en zona_chars
zonas_B = {}

for clave in sorted(pantallas, key=sort_key):
    d = pantallas[clave]
    zona_B = make_zona_B_entry(d['texto'], d['ty_offset'], d['max_chars'],
                                zona_chars_index, zona_chars)
    zonas_B[clave] = zona_B

n_zona_chars = len(zona_chars)
bytes_zona_chars = n_zona_chars  # 1 byte por char
n_bancos_zona_chars = max(1, (bytes_zona_chars + 0xFFFF) // 0x10000)
print(f'zona_chars global: {len(zona_chars_index)} palabras unicas, '
      f'{n_zona_chars} chars = {bytes_zona_chars} bytes '
      f'({n_bancos_zona_chars} banco(s) de datos, {bytes_zona_chars/(n_bancos_zona_chars*65536)*100:.1f}% del ultimo)')
if n_bancos_zona_chars > 1:
    print(f'  (zona_chars se reparte en {n_bancos_zona_chars} bancos -- '
          f'ya no esta limitada a un solo banco de 64KB, ver make_zona_B_entry)')

# --- PASADA 2: escribir zona_chars una sola vez, luego zona_B por pantalla ---
# Layout:
#   Primeros n_bancos_zona_chars bancos de datos: zona_chars (1 byte por
#     char, repartida secuencialmente entre bancos si no entra en uno solo;
#     cada palabra queda entera dentro de un unico banco, nunca partida).
#   A continuacion (mismo banco donde termino zona_chars, o el siguiente si
#     no entra): zona_B pantalla 1 (6 bytes por ref), zona_B pantalla 2 ...

# Escribir zona_chars, avanzando de banco cuando se llena uno (mismo
# mecanismo de desborde que ya usa zona_B mas abajo).
for cidx in zona_chars:
    if pos >= 0x10000:
        nuevo_banco = siguiente_banco_datos(bancos_reales[banco_actual_idx])
        bancos_reales.append(nuevo_banco)
        banco_actual_idx += 1
        bancos_datos.append(bytearray(0x10000))
        pos = 0
        print(f'  -> zona_chars continua en banco 0x{nuevo_banco:02X}')
    banco_actual = bancos_datos[banco_actual_idx]
    banco_actual[pos] = cidx
    pos += 1

print(f'zona_chars escrita en banco(s) '
      f'{", ".join(f"0x{b:02X}" for b in bancos_reales)} '
      f'(offset final 0x{pos:04X} en el ultimo)')

# A partir de aca, bancos_reales[0 .. banco_actual_idx] son los bancos de
# zona_chars -- char_bank_idx (relativo) se traduce a banco real indexando
# esta misma lista.

# Escribir zona_B de cada pantalla
# Cada ref: tileset_addr_base(2b) + char_bank(1b) + char_offset(2b) + word_len(1b) = 6 bytes
for clave in sorted(pantallas, key=sort_key):
    d = pantallas[clave]
    etiqueta = f"{d['historia_nombre']}-P{d['pantalla']}"
    zona_B = zonas_B[clave]
    tam_necesario = len(zona_B) * 6

    if pos + tam_necesario > 0x10000:
        nuevo_banco = siguiente_banco_datos(bancos_reales[banco_actual_idx])
        bancos_reales.append(nuevo_banco)
        banco_actual_idx += 1
        bancos_datos.append(bytearray(0x10000))
        pos = 0
        print(f'  -> Banco 0x{bancos_reales[banco_actual_idx - 1]:02X} lleno, '
              f'continuando en banco 0x{nuevo_banco:02X}')

    banco_actual = bancos_datos[banco_actual_idx]
    bancos_de_pantalla[clave] = bancos_reales[banco_actual_idx]
    offsets[clave] = pos
    counts[clave] = len(zona_B)
    for tileset_base, char_bank_idx, char_off, wlen in zona_B:
        banco_actual[pos]   = tileset_base & 0xFF
        banco_actual[pos+1] = (tileset_base >> 8) & 0xFF
        banco_actual[pos+2] = bancos_reales[char_bank_idx] & 0xFF
        banco_actual[pos+3] = char_off & 0xFF
        banco_actual[pos+4] = (char_off >> 8) & 0xFF
        banco_actual[pos+5] = wlen & 0xFF
        pos += 6

    print(f'  {etiqueta}: zona_B={len(zona_B)} refs, '
          f'banco=0x{bancos_de_pantalla[clave]:02X} offset=0x{offsets[clave]:04X}')

n_bancos_usados = banco_actual_idx + 1
lista_bancos_hex = ', '.join(f'0x{b:02X}' for b in bancos_reales)
print(f'Bancos de datos usados: {n_bancos_usados} ({lista_bancos_hex})')

# Construir pant_tabla (banco BANCO_TABLA_INDICE, hoy 0x61), 14 bytes por entrada:
# ultimo_kanji(2) + primer_kanji(2) + count(2) + offset(2) + banco_datos(1) +
# historia(1) + ruta_ref(2) + produce_marca(1) + espera_marca(1)
# El byte de historia se agrega al FINAL para no alterar los offsets de los
# campos existentes (count, offset, banco) que el cave ya conocia en v7.
# ruta_ref (v19e) se agrega DESPUES de historia -- campo dedicado y exclusivo
# de PASE1 (desambiguacion de ruta), NUNCA leido por PASE2 (reset de 0x0CF0),
# asi se evita el bug de v19e-intento1 (reutilizar 'primer_kanji' para esto
# rompia el reset-check de PASE2 al chocar con un kanji real de otra pantalla).
# Centinela 0xFFFF = "esta fila no participa de la logica de ruta".
# produce_marca/espera_marca (v19e, segundo mecanismo): ver comentario junto
# al parseo del CSV mas arriba. Centinela 0xFF = "no participa".
banco_tabla_indice = bytearray(0x10000)
BYTES_POR_ENTRADA = 14
tabla_pos = 0
filas_meta = []  # v22: metadata por fila (mismo orden que pant_tabla)
for clave in sorted(pantallas, key=sort_key):
    d = pantallas[clave]
    ult = d['ultimo_kanji']
    prim = d['primer_kanji']
    cnt = counts[clave]
    off = offsets[clave]  # apunta directamente a zona_B
    banco = bancos_de_pantalla[clave]
    hist = d['historia']
    ruta_ref = d['ruta_ref']
    produce_marca = d['produce_marca']
    espera_marca = d['espera_marca']
    if tabla_pos >= 0xFFFF:
        print('ERROR: pant_tabla crecio mas alla de lo que TABLA_B puede '
              'direccionar (offset >= 0xFFFF) -- revisar diseno de v22')
        sys.exit(1)
    filas_meta.append({
        'offset': tabla_pos,
        'ultimo_kanji': ult,
        'primer_kanji': prim,
        'historia': hist,
        'ruta_ref': ruta_ref,
        'espera_marca': espera_marca,
    })
    banco_tabla_indice[tabla_pos]   = ult & 0xFF
    banco_tabla_indice[tabla_pos+1] = (ult >> 8) & 0xFF
    banco_tabla_indice[tabla_pos+2] = prim & 0xFF
    banco_tabla_indice[tabla_pos+3] = (prim >> 8) & 0xFF
    cnt_flag = cnt | FLAG_COMPRIMIDO
    banco_tabla_indice[tabla_pos+4] = cnt_flag & 0xFF
    banco_tabla_indice[tabla_pos+5] = (cnt_flag >> 8) & 0xFF
    banco_tabla_indice[tabla_pos+6] = off & 0xFF
    banco_tabla_indice[tabla_pos+7] = (off >> 8) & 0xFF
    banco_tabla_indice[tabla_pos+8] = banco & 0xFF
    banco_tabla_indice[tabla_pos+9] = hist & 0xFF
    banco_tabla_indice[tabla_pos+10] = ruta_ref & 0xFF
    banco_tabla_indice[tabla_pos+11] = (ruta_ref >> 8) & 0xFF
    banco_tabla_indice[tabla_pos+12] = produce_marca & 0xFF
    banco_tabla_indice[tabla_pos+13] = espera_marca & 0xFF
    tabla_pos += BYTES_POR_ENTRADA

print(f'pant_tabla: {n_pant} entradas x {BYTES_POR_ENTRADA} bytes = '
      f'{n_pant*BYTES_POR_ENTRADA} bytes en banco 0x{BANCO_TABLA_INDICE:02X}')

# ----------------------------------------------------------------------
# v22: Construir TABLA_A y TABLA_B (banco BANCO_TABLA_OPT) -- ver
# generar_horizontal_compresion_opt_v22.py (rama espanol) para la
# explicacion completa del diseno. Misma logica exacta, aca aplicada
# sobre filas_meta de esta rama (ingles).
# ----------------------------------------------------------------------
from collections import defaultdict as _defaultdict

_eventos = _defaultdict(list)
for _i, _fm in enumerate(filas_meta):
    _eventos[(_fm['ultimo_kanji'], _fm['historia'])].append((_i, 0))
    _eventos[(_fm['primer_kanji'], _fm['historia'])].append((_i, 1))

_tabla_b_entries = []
for (_valor, _hist), _evs in _eventos.items():
    _evs.sort()
    _idx0, _tipo0 = _evs[0]
    _ptr = filas_meta[_idx0]['offset'] if _tipo0 == 0 else 0xFFFF
    _tabla_b_entries.append((_valor, _hist, _ptr))
_tabla_b_entries.sort(key=lambda e: e[0])
N_TABLA_B = len(_tabla_b_entries)

_grupos_ambiguos = _defaultdict(list)
for _i, _fm in enumerate(filas_meta):
    if _fm['ruta_ref'] != 0xFFFF or _fm['espera_marca'] != 0xFF:
        _grupos_ambiguos[_fm['ultimo_kanji']].append(_i)
_tabla_a_index = sorted(_grupos_ambiguos.items(), key=lambda kv: kv[0])
N_TABLA_A = len(_tabla_a_index)
N_TABLA_A_ROWS = sum(len(v) for _, v in _tabla_a_index)

if N_TABLA_B > 0xFFFF or N_TABLA_A_ROWS > 0xFFFF or N_TABLA_A > 0xFFFF:
    print('ERROR: TABLA_A/TABLA_B exceden 65535 entradas -- revisar diseno')
    sys.exit(1)

banco_tabla_opt = bytearray(0x10000)
TABLA_A_INDEX_OFF = 0x0000
TABLA_A_ROWS_OFF = TABLA_A_INDEX_OFF + N_TABLA_A * 6
TABLA_B_OFF = TABLA_A_ROWS_OFF + N_TABLA_A_ROWS * 2
_fin_tabla_opt = TABLA_B_OFF + N_TABLA_B * 5
if _fin_tabla_opt > 0x10000:
    print(f'ERROR: TABLA_A+TABLA_B no entran en un banco de 64KB '
          f'({_fin_tabla_opt} bytes)')
    sys.exit(1)

_pos_rows = 0
for _gi, (_kanji, _indices) in enumerate(_tabla_a_index):
    _off_idx = TABLA_A_INDEX_OFF + _gi * 6
    _start = _pos_rows
    _count = len(_indices)
    banco_tabla_opt[_off_idx]   = _kanji & 0xFF
    banco_tabla_opt[_off_idx+1] = (_kanji >> 8) & 0xFF
    banco_tabla_opt[_off_idx+2] = _start & 0xFF
    banco_tabla_opt[_off_idx+3] = (_start >> 8) & 0xFF
    banco_tabla_opt[_off_idx+4] = _count & 0xFF
    banco_tabla_opt[_off_idx+5] = (_count >> 8) & 0xFF
    for _ri, _fila_idx in enumerate(_indices):
        _off_row = TABLA_A_ROWS_OFF + (_start + _ri) * 2
        _ptr_fila = filas_meta[_fila_idx]['offset']
        banco_tabla_opt[_off_row]   = _ptr_fila & 0xFF
        banco_tabla_opt[_off_row+1] = (_ptr_fila >> 8) & 0xFF
    _pos_rows += _count

for _bi, (_valor, _hist, _ptr) in enumerate(_tabla_b_entries):
    _off_b = TABLA_B_OFF + _bi * 5
    banco_tabla_opt[_off_b]   = _valor & 0xFF
    banco_tabla_opt[_off_b+1] = (_valor >> 8) & 0xFF
    banco_tabla_opt[_off_b+2] = _hist & 0xFF
    banco_tabla_opt[_off_b+3] = _ptr & 0xFF
    banco_tabla_opt[_off_b+4] = (_ptr >> 8) & 0xFF

print(f'TABLA_A: {N_TABLA_A} kanjis ambiguos, {N_TABLA_A_ROWS} filas -- '
      f'{N_TABLA_A*6 + N_TABLA_A_ROWS*2} bytes')
print(f'TABLA_B: {N_TABLA_B} pares (valor,historia) -- {N_TABLA_B*5} bytes')
print(f'Banco 0x{BANCO_TABLA_OPT:02X} (TABLA_A+TABLA_B): {_fin_tabla_opt} bytes usados de 65536')

# ----------------------------------------------------------------------
# Generar ASM
# El cave lee pant_tabla desde banco BANCO_TABLAS (definido en el ASM) offset 0x0000
# ----------------------------------------------------------------------
asm_template = f"""; cave_en.asm
; v18: compresion por contenido de palabra.
; zona_chars: char_idx por palabra unica (1 byte c/u). Ya NO esta limitada a
;   un solo banco -- puede repartirse en varios (julio 2026, ver comentario
;   "FIX GLOBAL zona_chars multibanco"); cada ref de zona_B dice en que
;   banco vive la palabra que referencia.
; zona_B: (tileset_addr_base 2b + char_bank 1b + char_offset 2b + word_len 1b)
;   = 6 bytes por ref (antes 5, sin char_bank -- banco fijo 0x43 asumido)
; Cave: por cada ref, incrementa tileset_addr += 0x100 por letra (fijo)
; FLAG_COMPRIMIDO = bit 15 del count en pant_tabla

BITS 16
ORG 0x4F802

BANCO_FUENTE    equ 0x{BANCO_FUENTE:02X}
BANCO_TABLAS    equ 0x{BANCO_TABLA_INDICE:02X}
N_PANT          equ {n_pant}
FLAG_COMPRIMIDO equ 0x8000
DELTA_TILESET   equ 0x0100   ; incremento tileset_addr entre letras consecutivas

; v22: tablas auxiliares de busqueda (ver "Construir TABLA_A / TABLA_B" en
; el Python). BANCO_TABLA_OPT es un banco NUEVO, separado de BANCO_TABLAS
; (pant_tabla no se toco). Todos los offsets son bytes dentro de ese banco.
BANCO_TABLA_OPT   equ 0x{BANCO_TABLA_OPT:02X}
N_TABLA_A         equ {N_TABLA_A}
TABLA_A_INDEX_OFF equ 0x{TABLA_A_INDEX_OFF:04X}
TABLA_A_ROWS_OFF  equ 0x{TABLA_A_ROWS_OFF:04X}
N_TABLA_B         equ {N_TABLA_B}
TABLA_B_OFF       equ 0x{TABLA_B_OFF:04X}

; NOTA (v19c): el mecanismo aislado del menu (MENU_PREV/MENU_CF, WRAM
; 0x0DBC/0x0DBD) de v19/v19b se ELIMINO -- dependia de que HOOK1 escribiera
; 0x0DB4 en cada dibujado para detectar el "flanco de entrada" al menu.
; Desde que la erradicacion del texto paso a hacerla HOOKCAP/HOOKRES
; chequeando es:[0x09D6] directamente (ver STUBCAP/STUBRES mas abajo),
; HOOK1 quedo como un no-op puro que NUNCA toca 0x0DB4.
; ES_MENU_ACTUAL (0x0DBE) tampoco se usa desde v19b -- la marca "es menu"
; se pasa por la pila (push/pop AX), no por RAM persistente. Ver
; comentarios en .seguir_dibujando y .suprimir_libro.
;
; FIX (v19c, hallado en pruebas en vivo tras la limpieza de arriba): sacar
; el bloque MENU_PREV/MENU_CF sin reemplazo reintrodujo un bug viejo del
; proyecto (documentado desde v19, antes de esta sesion): el flag global
; 0x0CF0 ("ya dibuje algo, no repetir") se comparte con TODO el texto
; narrativo del juego, y solo se resetea cuando el motor dispara el
; primer_kanji de OTRA fila -- eso NO pasa de forma confiable al navegar
; entre selecciones del menu. Confirmado en vivo: elegir H5 en un libro
; nuevo dibuja bien "COMENZAR HISTORIA" (pone 0x0CF0=1); volver atras y
; elegir H4 SI encuentra la fila correcta en la tabla, pero como 0x0CF0
; sigue en 1 de la vez anterior, el cave decide "ya dibuje esto" y NO
; redibuja -- pantalla en blanco. Mismo sintoma reportado al cambiar de
; libro y entrar a otra historia despues.
;
; Los kanjis de menu (mas abajo) ya NO dependen de 0x0CF0 en absoluto --
; usan su propio par de celdas (ULTIMO_KANJI_MENU/ULTIMO_HIST_MENU,
; reaprovechando WRAM 0x0DB4/0x0DBC, libres desde que se eliminaron el
; flag viejo de HOOK1 y MENU_PREV/MENU_CF): redibujan cada vez que la
; combinacion kanji+historia CAMBIA respecto de la ultima vez que se
; dibujo CUALQUIER kanji de menu, sin importar el estado de 0x0CF0. El
; resto del texto narrativo sigue exactamente igual que antes (0x0CF0
; sin tocar para esos casos).
; *** ESTO NO ES CODIGO MUERTO -- NO ELIMINAR EN UNA LIMPIEZA FUTURA ***
; Aunque ULTIMO_KANJI_MENU/ULTIMO_HIST_MENU reaprovechan direcciones que
; SI fueron dead code en algun momento (0x0DB4 del viejo HOOK1, 0x0DBC de
; MENU_PREV), estas 2 celdas activas cumplen una funcion real y necesaria
; ahora mismo: sin ellas, el menu vuelve a quedar en blanco al navegar
; entre historias/libros (bug confirmado, ver el bloque FIX de arriba).
; Antes de tocar/quitar esto, confirmar en vivo que la secuencia "elegir
; una historia, volver, elegir otra distinta" y "cambiar de libro y
; entrar a una historia" siguen mostrando el texto del menu correctamente.
ULTIMO_KANJI_MENU equ 0x0DB4   ; word: ultimo kanji de menu dibujado
ULTIMO_HIST_MENU  equ 0x0DBC   ; byte: historia asociada a ese ultimo dibujado

; NUEVO (v19e, REDISEÑADO): ULTIMA_PANTALLA_UK usa WRAM 0x0CF2 (confirmado
; en vivo que se puede escribir desde el cave, con una prueba incondicional).
; DESCARTADO el diseño anterior (ARRANQUE_KANJI/ARRANQUE_LOCK, que intentaba
; detectar "desde que kanji arranco el bloque actual"): confirmado en vivo
; que el cave NO ve de forma confiable el primer kanji de un bloque nuevo --
; hay un tramo de kanjis intermedios (transicion de pantalla/animacion) que
; nunca disparan el hook, y en el caso de H5 P54->P55 vs P71->P72 ambas
; rutas convergen en el MISMO kanji real (0x0DA8) como primer caracter
; visible, haciendolas indistinguibles por "donde arranco".
;
; Nuevo enfoque: en vez de "donde arranco este bloque", guardar CUAL FUE LA
; ULTIMA PANTALLA (fila de pant_tabla) que se dibujo con EXITO -- esto se
; actualiza en .seguir_dibujando, el mismo lugar que ya funciona de forma
; comprobada para TODO el texto narrativo existente (no depende de detectar
; ningun kanji intermedio nuevo). Guarda el ultimo_kanji de esa fila.
;
; Para desambiguar dos filas que comparten el mismo ultimo_kanji, se usa un
; campo NUEVO Y DEDICADO en pant_tabla: 'ruta_ref' (bytes 10-11 de cada
; entrada, ver construccion de la tabla en Python). NO se reutiliza
; 'primer_kanji' (intento anterior, revertido): ese campo lo sigue leyendo
; PASE 2 para el reset de 0x0CF0 con CUALQUIER kanji real que pase por el
; cave, y reutilizarlo para esta desambiguacion causaba que un kanji real
; de OTRA pantalla (ej. el propio ultimo_kanji de P71D en la ruta corta)
; disparara por error el reset-check de una fila no relacionada (H5;55A),
; cortando el escaneo de PASE 2 antes de llegar a la fila correcta.
; 'ruta_ref' es un campo aparte que PASE 2 nunca toca, asi que no puede
; chocar con ningun kanji real de ninguna pantalla.
;
; ruta_ref indica "el ultimo_kanji de la pantalla que deberia haberse
; dibujado justo antes, en la ruta a la que corresponde esta fila" -- ej.
; H5;55 (ruta larga, viene despues de P54) usa ruta_ref = ultimo_kanji de
; P54 (0x0B73); H5;55A (ruta corta, viene despues de P71D) usa ruta_ref =
; ultimo_kanji de P71D (0x0D91). Filas sin desambiguacion usan el
; centinela 0xFFFF (no participan de PASE 1).
; Ver .buscar1 mas abajo (PASE 1). Si ninguna fila comparte ultimo_kanji,
; este valor no se usa para nada (el .buscar de siempre encuentra la unica
; coincidencia en la primera pasada, sin cambios de comportamiento).
ULTIMA_PANTALLA_UK equ 0x0CF2   ; word: ultimo_kanji de la ultima fila dibujada con exito

; NUEVO (v19e, segundo mecanismo de desambiguacion): ULTIMA_MARCA_RUTA.
; Cubre el caso en que DOS filas duplicadas (ej. version larga/corta de una
; misma pantalla compartida) ya dejaron el MISMO valor real en
; ULTIMA_PANTALLA_UK (porque ambas terminan en el mismo kanji real) -- en
; ese caso una tercera fila no puede usar ruta_ref/ULTIMA_PANTALLA_UK para
; saber cual de las dos se dibujo, porque ambas producen el mismo valor.
; ULTIMA_MARCA_RUTA guarda en cambio un numero INVENTADO por nosotros (no
; un kanji real), que cada fila puede declarar via 'produce_marca' (ver
; .seguir_dibujando) -- como nunca se compara contra bx (kanji real), no
; puede chocar con contenido de ninguna pantalla. 0x0CF4 confirmado
; escribible en vivo con una prueba incondicional (misma prueba que
; confirmo 0x0CF2).
ULTIMA_MARCA_RUTA equ 0x0CF4   ; byte: ultima "marca" de ruta producida (invented, no es kanji)

cave_start:
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    push es
    push ds

    cmp  ax, 0x00FE
    je   .es_kanji
    jmp  .fin

.es_kanji:
    xor  bx, bx
    mov  es, bx
    mov  bx, word [es:0x09DC]
    mov  dh, byte [es:0x09D8]

    ; FIX (v20): el kanji 0x0069 dispara tanto en la pantalla normal
    ; "COMENZAR HISTORIA" (1 opcion) como en la pantalla de 2 opciones
    ; ("empezar esta historia" / "releer todas las historias desde el
    ; principio") -- confirmado en vivo que ambas comparten el mismo
    ; kanji nativo. Se diferencian por es:[0x0A2A] (0=normal, 1=variante
    ; de 2 opciones; 2=pantalla propia de H6, sin relacion con esto).
    ; Para no tocar el formato de pant_tabla (10 bytes/entrada, sin campo
    ; libre para este flag), se resuelve ajustando "dh" ANTES de buscar en
    ; la tabla: si es la variante de 2 opciones, se le suma 0x10 a dh, y
    ; las filas del CSV para esa variante usan historia "H1B".."H5B"
    ; (mapeadas a 0x10..0x14) en vez de "H1".."H5". Esto hace que el
    ; .buscar de mas abajo encuentre automaticamente la fila correcta sin
    ; ningun cambio en la logica de matching ni en el tamano de entrada.
    cmp  bx, 0x0069
    jne  .no_variante_69
    cmp  word [es:0x0A2A], 0x0001
    jne  .no_variante_69
    add  dh, 0x10
.no_variante_69:

    ; FIX (v20): mismo problema, otro kanji. Las 2 confirmaciones SI/NO
    ; del menu de pausa ("reiniciar esta historia" y "reiniciar todas las
    ; historias") comparten el kanji 0x0060 (ademas de 0x30/0x64, que ya
    ; se dejan sin traducir por ser genericos). El kanji 0x0056 SI es
    ; exclusivo de la confirmacion de "reiniciar todas" (confirmado en
    ; vivo capturando la secuencia completa de escrituras a es:[0x9DC] en
    ; cada pantalla) -- esa fila NO necesita gate, se deja con su kanji
    ; normal. Para "reiniciar esta historia" (que no tiene ningun kanji
    ; exclusivo) se usa 0x0060 + el flag es:[0x0A16].
    ;
    ; IMPORTANTE: el gate NO usa es:[0x09E6] (que se probo primero por
    ; parecer el flag logico -- distinguia 01/02 correctamente en el
    ; Memory Viewer en reposo) porque en la practica nunca coincidio ni
    ; con 0x0001 ni con 0x0002 en el instante exacto del dibujado del
    ; kanji -- probablemente el juego lo actualiza recien DESPUES de ese
    ; primer dibujado. es:[0x0A16] es la posicion del cursor en el menu
    ; de 3 opciones al momento de apretar Enter (00="continuar",
    ; 01="reiniciar esta historia", 02="reiniciar todas"), que se fija
    ; ANTES de la transicion a la pantalla SI/NO y SI esta disponible a
    ; tiempo. Confirmado funcionando en vivo por el usuario.
    ;
    ; Mismo truco que con 0x0069/es:[0x0A2A]: se le suma 0x20 a dh (offset
    ; distinto al 0x10 de la variante de 0x69, para no mezclar los dos
    ; casos), y las filas del CSV para esta variante usan historia
    ; "H1C".."H5C" (mapeadas a 0x20..0x24).
    ;
    ; FIX (v20f): es:[0x0A16] NO es exclusivo del menu de pausa -- es una
    ; celda de cursor generica que reutilizan otros menus de seleccion.
    ; Confirmado en vivo: al elegir la 2da opcion del menu de 2 opciones
    ; ("releer historias desde el inicio", kanji 0x069 + es:[0x0A2A]==1)
    ; y entrar a su propia confirmacion SI/NO (kanji 0x056, sin gate),
    ; es:[0x0A16] TAMBIEN vale 0x0001 ahi (el cursor arranca en "NO").
    ; Como el kanji 0x0060 tambien aparece en esa pantalla (es generico,
    ; igual que 0x30/0x64), el gate disparaba por error y pisaba el texto
    ; correcto de 0x056 con el de "reiniciar esta historia" un instante
    ; despues. Se agrega una segunda condicion: es:[0x0A2A] debe ser
    ; distinto de 0x0001 (confirmado en vivo que vale 0x0000 en el menu
    ; de pausa real, y 0x0001 en el menu de 2 opciones) para asegurar que
    ; estamos realmente en el menu de pausa y no en el de 2 opciones.
    cmp  bx, 0x0060
    jne  .no_variante_60
    cmp  word [es:0x0A16], 0x0001
    jne  .no_variante_60
    cmp  word [es:0x0A2A], 0x0001
    je   .no_variante_60
    add  dh, 0x20
.no_variante_60:

    in   al, 0xC3
    push ax                       ; guardar banco original del motor (igual que v21)

    ; =======================================================================
    ; v22: PASE1/PASE1B/PASE2 optimizados con tablas auxiliares (TABLA_A,
    ; TABLA_B -- generadas en Python, ver "Construir TABLA_A / TABLA_B").
    ; Reemplaza los 3 recorridos lineales completos de v21 (hasta ~3 x N_PANT
    ; comparaciones por kanji dibujado) por:
    ;   (a) un escaneo lineal TRIVIAL del indice de TABLA_A (hoy N_TABLA_A
    ;       kanjis, un punado) para saber si bx participa de PASE1/PASE1B,
    ;       seguido -- solo si participa -- de la MISMA logica de PASE1/
    ;       PASE1B de v21 pero restringida a ese grupo chico de filas.
    ;   (b) si no aplica (a), una busqueda BINARIA en TABLA_B (N_TABLA_B
    ;       entradas) equivalente a PASE2. TABLA_B se genero en el Python
    ;       simulando EXACTAMENTE el orden/prioridad de PASE2 original
    ;       (incluido el caso donde una fila anterior con primer_kanji==bx
    ;       gana por orden de tabla a una fila posterior con
    ;       ultimo_kanji==bx -- ver comentario en el generador).
    ; El comportamiento observable es identico al de v21; solo cambia
    ; cuantas comparaciones hacen falta para llegar a el.
    ; =======================================================================

    mov  al, BANCO_TABLA_OPT
    out  0xC3, al
    mov  ax, 0x3000
    mov  ds, ax

    mov  di, TABLA_A_INDEX_OFF
    mov  cx, N_TABLA_A
.opt_a_buscar:
    jcxz .opt_a_cx_cero
    jmp  .opt_a_seguir
.opt_a_cx_cero:
    jmp  .opt_tabla_b
.opt_a_seguir:
    cmp  word [ds:di], bx
    je   .opt_a_grupo_encontrado
    add  di, 6
    dec  cx
    jmp  .opt_a_buscar

.opt_a_grupo_encontrado:
    ; ds = BANCO_TABLA_OPT; di = entrada de indice (kanji,start,count)
    mov  ax, word [ds:di+2]       ; start (indice de fila dentro de ROWS)
    mov  cx, word [ds:di+4]       ; count (filas ambiguas de este kanji)
    shl  ax, 1                    ; ROWS = punteros de 2 bytes
    add  ax, TABLA_A_ROWS_OFF
    mov  bp, ax                   ; bp = base constante del grupo (offset en banco OPT)
    mov  ah, cl                   ; ah = copia constante de count (grupos son chicos)

    ; --- PASE 1 (ruta_ref), restringido al grupo ---
    mov  si, bp
    mov  dl, ah
.opt_p1_loop:
    or   dl, dl
    jnz  .opt_p1_seguir
    jmp  .opt_p1_fin
.opt_p1_seguir:
    mov  di, word [ds:si]         ; di = offset de la fila candidata en pant_tabla
    mov  al, BANCO_TABLAS
    out  0xC3, al
    mov  al, byte [ds:di+9]
    cmp  al, dh
    jne  .opt_p1_sig
    push bx
    mov  bx, word [es:ULTIMA_PANTALLA_UK]
    cmp  word [ds:di+10], bx
    pop  bx
    je   .opt_p1_hit
.opt_p1_sig:
    mov  al, BANCO_TABLA_OPT
    out  0xC3, al
    add  si, 2
    dec  dl
    jmp  .opt_p1_loop
.opt_p1_hit:
    mov  si, di                   ; ds ya = BANCO_TABLAS, si = fila encontrada
    jmp  .encontrado
.opt_p1_fin:
    ; ds = BANCO_TABLA_OPT aca (garantizado por .opt_p1_sig o por dl==0 de entrada)

    ; --- PASE 1B (espera_marca), restringido al mismo grupo ---
    mov  si, bp
    mov  dl, ah
.opt_p1b_loop:
    or   dl, dl
    jnz  .opt_p1b_seguir
    jmp  .opt_tabla_b
.opt_p1b_seguir:
    mov  di, word [ds:si]
    mov  al, BANCO_TABLAS
    out  0xC3, al
    mov  al, byte [ds:di+9]
    cmp  al, dh
    jne  .opt_p1b_sig
    mov  al, byte [ds:di+13]
    cmp  al, 0xFF
    je   .opt_p1b_sig
    mov  ah, byte [es:ULTIMA_MARCA_RUTA]
    cmp  al, ah
    je   .opt_p1b_hit
.opt_p1b_sig:
    mov  al, BANCO_TABLA_OPT
    out  0xC3, al
    add  si, 2
    dec  dl
    jmp  .opt_p1b_loop
.opt_p1b_hit:
    mov  si, di
    jmp  .encontrado

.opt_tabla_b:
    ; ds = BANCO_TABLA_OPT (garantizado en todos los caminos que llegan aca)
    ; Busqueda binaria por 'valor' (bx) en TABLA_B, [lo=ax, hi=cx) semiabierto
    xor  ax, ax
    mov  cx, N_TABLA_B
.opt_b_bsearch:
    cmp  ax, cx
    jb   .opt_b_bsearch_sigue
    jmp  .opt_b_reset
.opt_b_bsearch_sigue:
    mov  di, cx
    sub  di, ax
    shr  di, 1
    add  di, ax                   ; di = mid = lo + (hi-lo)/2
    mov  si, di
    shl  si, 2
    add  si, di                   ; si = mid*5 (mid*4 + mid)
    add  si, TABLA_B_OFF
    mov  bp, word [ds:si]         ; bp = valor de esta entrada
    cmp  bp, bx
    je   .opt_b_encontrado_valor
    jb   .opt_b_ir_mayor
    mov  cx, di                   ; bp > bx -> hi = mid
    jmp  .opt_b_bsearch
.opt_b_ir_mayor:
    mov  ax, di
    inc  ax                       ; bp < bx -> lo = mid+1
    jmp  .opt_b_bsearch

.opt_b_encontrado_valor:
    ; hallamos UNA entrada con valor==bx; puede haber varias contiguas (una
    ; por historia distinta) -- retroceder hasta el principio del bloque y
    ; escanear hacia adelante buscando historia==dh.
    mov  di, si
.opt_b_retro:
    cmp  di, TABLA_B_OFF
    je   .opt_b_avanza
    mov  bp, di
    sub  bp, 5
    cmp  word [ds:bp], bx
    jne  .opt_b_avanza
    mov  di, bp
    jmp  .opt_b_retro
.opt_b_avanza:
    cmp  di, TABLA_B_OFF + N_TABLA_B*5
    jb   .opt_b_avanza_ok1
    jmp  .opt_b_reset
.opt_b_avanza_ok1:
    cmp  word [ds:di], bx
    je   .opt_b_avanza_ok2
    jmp  .opt_b_reset
.opt_b_avanza_ok2:
    mov  al, byte [ds:di+2]
    cmp  al, dh
    je   .opt_b_scan_hit
    add  di, 5
    jmp  .opt_b_avanza
.opt_b_scan_hit:
    mov  si, word [ds:di+3]       ; si = offset de la fila en pant_tabla, o 0xFFFF=reset
    cmp  si, 0xFFFF
    je   .opt_b_reset
    mov  al, BANCO_TABLAS
    out  0xC3, al
    jmp  .encontrado
.opt_b_reset:
    xor  ax, ax
    mov  es, ax
    mov  word [es:0x0CF0], 0x0000
    jmp  .fin_restaurar

.encontrado:
    xor  ax, ax
    mov  es, ax
    ; FIX (v19c): los kanjis de menu conocidos (3 opciones, 1 opcion,
    ; las 2 confirmaciones SI/NO, y la pantalla propia de H6) NO usan el
    ; flag global 0x0CF0 -- ver nota junto a ULTIMO_KANJI_MENU/
    ; ULTIMO_HIST_MENU mas arriba (por que: 0x0CF0 se queda "pegado" al
    ; navegar entre selecciones del menu y bloquea el redibujado). Para
    ; cualquier otro kanji (texto narrativo), sigue el chequeo estandar
    ; de 0x0CF0 de siempre, sin cambios.
    cmp  bx, 0x003A
    je   .es_menu_kanji
    cmp  bx, 0x0069
    je   .es_menu_kanji
    cmp  bx, 0x0056
    je   .es_menu_kanji
    cmp  bx, 0x0060
    je   .es_menu_kanji
    cmp  bx, 0x0064
    je   .es_menu_kanji
    cmp  bx, 0x00B4
    je   .es_menu_kanji
    ; NUEVO (v19e): 0x00A4 es la SEGUNDA pantalla propia del menu de H6
    ; ("ENTRAR MANSION", H6;1457) -- 0x00B4 (la primera, "CONTINUAR/ENTRAR
    ; EN MANSION", H6;1456) ya estaba en esta lista, pero 0x00A4 no, asi
    ; que quedaba sujeta al flag normal 0x0CF0 (igual que texto narrativo)
    ; en vez del tratamiento de menu (redibujado en cada cambio). Eso
    ; explica el bug confirmado en vivo (presente incluso sin ningun
    ; cambio nuestro, en v19d): al seleccionar H6 y volver atras, esta
    ; pantalla puntual dejaba de redibujarse porque 0x0CF0 ya estaba en 1
    ; y nada lo reseteaba para ella especificamente.
    cmp  bx, 0x00A4
    je   .es_menu_kanji
    cmp  word [es:0x0CF0], 0x0001
    jne  .seguir_dibujando
    jmp  .fin_restaurar

.es_menu_kanji:
    cmp  word [es:ULTIMO_KANJI_MENU], bx
    jne  .menu_cambio
    mov  al, byte [es:ULTIMO_HIST_MENU]
    cmp  al, dh
    je   .menu_sin_cambio
.menu_cambio:
    ; NUEVO (v19e): forzar es:[0x09D6]=0 en el flanco de "kanji de menu
    ; distinto al ultimo dibujado" -- corrige el caso de volver al menu
    ; despues de creditos/marcador (limitacion conocida desde v19c). El
    ; problema de H6 (su texto se borra al seleccionarlo y volver atras)
    ; se confirmo presente TAMBIEN en v19d sin ningun cambio nuestro --
    ; es un bug preexistente, no relacionado con este fix. Sin exclusiones.
    xor  ax, ax
    mov  word [es:0x09D6], ax
    mov  word [es:ULTIMO_KANJI_MENU], bx
    mov  byte [es:ULTIMO_HIST_MENU], dh
    jmp  .seguir_dibujando
.menu_sin_cambio:
    jmp  .fin_restaurar

.seguir_dibujando:
    ; FIX v19b: la marca "es menu" (usada mas abajo en .suprimir_libro
    ; para no tocar 0x0C7E si lo que se dibujo fue el menu) ya NO se
    ; guarda en una posicion de RAM persistente (ES_MENU_ACTUAL) -- se
    ; pasa por la PILA, local a este unico dibujado, para que ninguna
    ; otra ejecucion (por ejemplo una interrupcion que reentre el cave
    ; en medio de este dibujado) pueda dejarla en un valor viejo. AX ya
    ; trae la marca (0 o 1) puesta justo arriba, antes de llegar aca.
    push ax                          ; [MENU-MARK] -- recuperado en .suprimir_libro
    mov  word [es:0x0CF0], 0x0001

    ; NUEVO (v19e, rediseñado): este bloque se acaba de dibujar con exito --
    ; guardar su propio ultimo_kanji (=bx, el kanji actual, ya que llegamos
    ; aca via un match de ultimo_kanji) en ULTIMA_PANTALLA_UK. Esto es lo
    ; que usa el PASE 1 de .buscar para desambiguar filas que comparten
    ; ultimo_kanji, en base a cual fue la ultima pantalla dibujada antes.
    mov  word [es:ULTIMA_PANTALLA_UK], bx

    ; NUEVO (v19e, segundo mecanismo): si esta fila declara 'produce_marca'
    ; (si+12, centinela 0xFF = no participa), anotar ese numero inventado
    ; en ULTIMA_MARCA_RUTA. AX ya esta libre aca (su valor util se guardo
    ; en la pila con el push de arriba), asi que se puede usar sin cuidado.
    mov  al, byte [ds:si+12]
    cmp  al, 0xFF
    je   .sin_marca_ruta
    mov  byte [es:ULTIMA_MARCA_RUTA], al
.sin_marca_ruta:

    mov  cx, word [ds:si+4]
    mov  di, word [ds:si+6]
    mov  dl, byte [ds:si+8]

    push cx
    push si
    push ds
    push dx
    xor  ax, ax
    mov  es, ax
    mov  di, 0x3000
    mov  cx, 0x0800
    rep  stosw
    pop  dx
    pop  ds
    pop  si
    pop  cx

    mov  di, word [ds:si+6]

    mov  al, dl
    out  0xC3, al
    mov  ax, 0x3000
    mov  es, ax

    test cx, FLAG_COMPRIMIDO
    jne  .rama_comprimida

    ; --- RAMA NORMAL (formato v17) ---
    mov  si, di
.loop:
    mov  di, word [es:si]
    add  si, 2
    mov  bl, byte [es:si]
    inc  si
    xor  bh, bh
    shl  bx, 4

    push cx
    push si
    push dx

    mov  al, BANCO_FUENTE
    out  0xC3, al
    mov  ax, 0x3000
    mov  ds, ax
    mov  si, bx
    xor  ax, ax
    mov  es, ax
    mov  cx, 8
.copy:
    mov  ax, word [ds:si]
    mov  word [es:di], ax
    add  si, 2
    add  di, 2
    loop .copy

    pop  dx
    mov  al, dl
    out  0xC3, al
    mov  ax, 0x3000
    mov  es, ax
    push cs
    pop  ds

    pop  si
    pop  cx
    loop .loop
    jmp  .suprimir_libro

    ; --- RAMA COMPRIMIDA ---
    ; di = offset zona_B, dl = banco datos, es = 0x3000 (banco datos)
    ; zona_chars: banco variable por palabra, ver char_bank en cada ref
.rama_comprimida:
    and  cx, 0x7FFF          ; cx = count_refs
    mov  si, di              ; si = puntero zona_B (avanza 6 bytes por ref)

.loop_refs:
    ; Leer ref: tileset_addr_base(2b) + char_bank(1b) + char_offset(2b) + word_len(1b) = 6 bytes
    mov  di, word [es:si]    ; di = tileset_addr_base
    add  si, 2
    mov  dh, byte [es:si]    ; dh = banco de zona_chars para esta palabra
    inc  si
    mov  bx, word [es:si]    ; bx = char_offset en zona_chars (dentro de ese banco)
    add  si, 2
    xor  ah, ah
    mov  al, byte [es:si]    ; al = word_len
    inc  si

    push cx                  ; [A] count_refs
    push si                  ; [B] puntero siguiente ref
    xor  ch, ch
    mov  cl, al              ; cx = word_len

.loop_chars:
    ; Leer char_idx desde zona_chars (banco variable, en dh)
    ; dl = banco zona_B, dh = banco zona_chars -- se preservan juntos en dx,
    ; dh se recarga por palabra en .loop_refs y no se toca hasta la proxima
    ; palabra, asi que sigue valiendo para todos los caracteres de esta.
    push dx                  ; [tmp] preservar banco zona_B (dl) + banco zona_chars (dh)
    mov  al, dh
    out  0xC3, al
    mov  ax, 0x3000
    mov  es, ax
    xor  ah, ah
    mov  al, byte [es:bx]    ; al = char_idx
    inc  bx
    shl  ax, 4               ; ax = char_idx * 16
    pop  dx                  ; [tmp] restaurar banco zona_B (dl) + banco zona_chars (dh)
    mov  si, ax              ; si = char_idx*16 en banco fuente

    push cx                  ; [C] word_len restante
    push bx                  ; [D] puntero zona_chars siguiente char
    push di                  ; [E] tileset_addr actual
    push dx                  ; [F] banco datos

    ; Copiar tile desde banco fuente a tileset_addr en RAM
    mov  si, ax              ; si = char_idx*16 en banco fuente
    mov  al, BANCO_FUENTE
    out  0xC3, al
    mov  ax, 0x3000
    mov  ds, ax
    xor  ax, ax
    mov  es, ax              ; es = RAM
    mov  cx, 8
.copy2:
    mov  ax, word [ds:si]
    mov  word [es:di], ax
    add  si, 2
    add  di, 2
    loop .copy2

    pop  dx
    mov  al, dl
    out  0xC3, al
    mov  ax, 0x3000
    mov  es, ax              ; es = banco datos
    push cs
    pop  ds

    pop  di                  ; [E] tileset_addr actual
    pop  bx                  ; [D] puntero zona_chars
    pop  cx                  ; [C] word_len restante

    ; Avanzar tileset_addr a la siguiente fila (incremento fijo 0x100)
    add  di, DELTA_TILESET

    loop .loop_chars

    pop  si                  ; [B] puntero siguiente ref
    pop  cx                  ; [A] count_refs
    dec  cx
    jne  .loop_refs_cont
    jmp  .suprimir_libro
.loop_refs_cont:
    jmp  .loop_refs

.suprimir_libro:
    ; FIX (julio 2026, v18_menutest3, revisado en v19b): 0x0C7E es una
    ; variable REAL del motor del juego (no nuestra), ya usada por el fix
    ; del libro animado para suprimirlo en la pantalla donde corresponde.
    ; El libro no aparece en el menu, asi que el dibujado del menu no debe
    ; tocarla -- si lo hace, desincroniza el estado del libro justo antes
    ; de pasar a la primera pantalla de la historia, mostrando basura
    ; grafica que tapa el texto.
    ;
    ; v19b: la marca "es menu" ya NO se lee de una posicion de RAM
    ; persistente -- se recupera de la PILA (empujada en .seguir_dibujando,
    ; ver comentario ahi), local a este unico dibujado. Evita que una
    ; reentrada del cave (por ejemplo via interrupcion) deje la marca en
    ; un valor viejo entre el momento en que se pone y el momento en que
    ; se usa.
    pop  ax                         ; [MENU-MARK] recupera la marca de .seguir_dibujando
    xor  bx, bx
    mov  es, bx
    cmp  al, 0x01
    je   .saltar_supresion_libro
    mov  word [es:0x0C7E], 0x0000
.saltar_supresion_libro:

.fin_restaurar:
    pop  ax
    out  0xC3, al

.fin:
    xor  bx, bx
    mov  es, bx
    mov  word [es:0x0C94], ax
    pop  ds
    pop  es
    pop  di
    pop  si
    pop  dx
    pop  cx
    pop  bx
    pop  ax
    ; FIX GLOBAL (julio 2026): este AX es el byte original de la tabla
    ; legacy en $FF370 (el mismo que empujamos en el primerisimo "push ax"
    ; de cave_start), y es lo que el llamador usa un instante despues para
    ; el "OUT 0xC3,AL" final en 0x340D88. La tabla fue diseniada para
    ; hardware de 64 bancos (6 bits); con la ROM expandida a 128 bancos,
    ; cualquier entrada con el bit 0x40 prendido selecciona un banco de la
    ; zona expandida (posiblemente uno de nuestros bancos de datos) en vez
    ; del banco original. Enmascarar aca, DESPUES de que ya paso el chequeo
    ; "CMP AX,0x00FE / JE .es_kanji" de mas arriba (que necesita ver el
    ; byte SIN enmascarar para reconocer el marcador de kanji), corrige
    ; todas las entradas de esa tabla de una sola vez sin romper el
    ; disparador del cave -- a diferencia de angostar la mascara compartida
    ; en 0x340D81 (intentado y descartado: ese AX es el mismo que ve el
    ; chequeo de arriba, y 0xFE & 0x3F ya no da 0xFE, asi que el cave
    ; dejaba de dispararse por completo).
    and  al, 0x3F
    ret
"""

os.makedirs('src', exist_ok=True)
with open(CAVE_ASM, 'w', encoding='utf-8', newline='\n') as f:
    f.write(asm_template)
print(f'ASM generado: {CAVE_ASM}')

r = subprocess.run(['nasm', '-f', 'bin', CAVE_ASM, '-o', CAVE_BIN],
                   capture_output=True, text=True)
if r.returncode != 0:
    print('ERROR NASM:', r.stderr)
    sys.exit(1)

cave = open(CAVE_BIN, 'rb').read()
print(f'Cave ensamblado: {len(cave)} bytes (limite: 2045)')
if len(cave) > 2045:
    print('ERROR: cave excede espacio disponible en banco 0x4F')
    sys.exit(1)

# ----------------------------------------------------------------------
# Parchear ROM
# ----------------------------------------------------------------------
rom = bytearray(open(ROM_INPUT, 'rb').read())
fuente = open(FUENTE_BIN, 'rb').read()

# Direcciones calculadas a partir de las constantes (no hardcodear, asi si
# en el futuro se cambian los bancos no se desincronizan las escrituras).
FUENTE_BASE = BANCO_FUENTE * 0x10000
TABLA_BASE  = BANCO_TABLA_INDICE * 0x10000
TABLA_OPT_BASE = BANCO_TABLA_OPT * 0x10000
rom[FUENTE_BASE:FUENTE_BASE+len(fuente)] = fuente
rom[TABLA_BASE:TABLA_BASE+len(banco_tabla_indice)] = banco_tabla_indice
rom[TABLA_OPT_BASE:TABLA_OPT_BASE+len(banco_tabla_opt)] = banco_tabla_opt
print(f'TABLA_A+TABLA_B escritas en banco 0x{BANCO_TABLA_OPT:02X} '
      f'(ROM offset 0x{TABLA_OPT_BASE:06X})')

for i, banco_bytes in enumerate(bancos_datos):
    banco_num = bancos_reales[i]
    base_addr = banco_num * 0x10000
    rom[base_addr:base_addr+len(banco_bytes)] = banco_bytes
    print(f'Banco 0x{banco_num:02X} escrito en ROM offset 0x{base_addr:06X}')

rom[0x34F802:0x34F802+len(cave)] = cave
rom[0x74F802:0x74F802+len(cave)] = cave

for base in [0x340D84, 0x740D84]:
    rom[base+0] = 0xE8
    rom[base+1] = 0x7B
    rom[base+2] = 0xEA
    rom[base+3] = 0x90

# === v9: TABLA PROPIA PARA EL LIBRO (2026-06-27, sesion 2) ===
#
# Tras investigacion extensa, se encontro que el libro animado se activa
# mediante un comando del stream de texto que escribe un PUNTERO en RAM
# (0x09EC). El motor lee 2 bytes desde ese puntero, los suma para obtener
# el "total de frames" de la animacion, y usa un tercer byte como "valor
# de reinicio" del contador al completar el ciclo. Ese contador alimenta
# directamente el indice (0x0C62) que usa el blitter generico para
# calcular que dibujar.
#
# Zerear los datos originales del libro (0x2CF000/0x6CF000) rompia el
# motor al intentar seguir el puntero original hacia una zona vacia
# (freeze reproducible, confirmado en H2 ruta alternativa y creditos).
#
# Este parche en cambio REDIRIGE el puntero (0x09EC) hacia una TABLA
# PROPIA de 3 bytes (en nuestro espacio de cave, no en datos ajenos del
# juego). Los valores de esta tabla (0x01, 0x06, 0x02) fueron copiados
# deliberadamente de una zona de ROM que se confirmo en vivo produce el
# resultado deseado (libro no visible, sin freeze, sin romper pausa de
# input ni desincronizar texto) -- a diferencia de depender de un valor
# de puntero que coincide por casualidad con datos ajenos no controlados,
# esta tabla es nuestra, documentada, y estable independientemente de
# cualquier cambio futuro en el resto de la ROM.
#
# Los datos originales del libro en ROM (0x2CF000/0x6CF000) quedan
# COMPLETAMENTE INTACTOS -- no se zerea nada.
#
# Conocido: existe un defecto visual preexistente en H2-P1 (corrupcion
# leve sobre BG1 al inicio de esa pantalla especifica) que se confirmo
# presente INCLUSO con el zereo original -- no es introducido por este
# parche, es un comportamiento ya existente del juego/motor en esa
# pantalla particular, pendiente de investigar por separado.
#
# Direcciones (banco original 0x34 y espejo 0x74):
#   Tabla: 0x34FE00 / 0x74FE00 (3 bytes) -- movida desde 0x34F992 en julio
#   2026 (FIX GLOBAL de mascara: el cave crecio 2 bytes por el "AND AL,0x3F"
#   agregado antes del RET, y eso choco contra la tabla del libro que estaba
#   pegada justo al final del cave sin margen). Se verifico que TODA la cola
#   del banco 0x34 desde 0x34F802 en adelante esta libre (0xFF) en la ROM
#   original hasta el final del banco, asi que se movio la tabla bien lejos
#   del cave (0x34FE00) para no volver a chocar con cada pequenio ajuste
#   futuro del cave.
#   Puntero redirigido en: 0x34172D-0x34172E y 0x341757-0x341758 (y espejos)

# PRUEBA v19b (julio 2026): antes esta tabla sumaba 7 (0x01+0x06), a
# proposito FUERA del rango normal de animacion (0-4), para forzar el
# modo "invisible" del contador -- un camino de codigo no entendido del
# todo (ver doc 2026-06-27_libro_animado_solucion_v9.md, seccion 4).
# Ahora que los datos graficos originales del libro estan en cero (ver
# mas abajo), se prueba con valores DENTRO del rango normal (suma 4) para
# que el motor siga su camino de animacion habitual -- y como los datos
# que lee son todos cero, deberia dibujar tiles vacios en cada frame,
# desde el primero, sin depender del caso limite "fuera de rango".
TABLA_LIBRO = bytes([0x01, 0x06, 0x02])  # v19d: revertido al valor de v19 --
                                          # ver nota "REVERTIDO EN v19d" antes
                                          # del zereo mas abajo, mismo motivo.
DIR_TABLA_LIBRO = 0x34FE00
for base_tabla in [DIR_TABLA_LIBRO, DIR_TABLA_LIBRO + 0x400000]:
    rom[base_tabla:base_tabla+len(TABLA_LIBRO)] = TABLA_LIBRO

PUNTERO_TABLA_LIBRO = DIR_TABLA_LIBRO - 0x340000  # offset CPU dentro del banco
for base_instr in [0x34172D, 0x341757, 0x74172D, 0x741757]:
    assert rom[base_instr] == 0xCC and rom[base_instr+1] == 0x11, (
        f"Bytes inesperados en 0x{base_instr:06X}: "
        f"{rom[base_instr]:02X} {rom[base_instr+1]:02X} (se esperaba CC 11)"
    )
    rom[base_instr] = PUNTERO_TABLA_LIBRO & 0xFF
    rom[base_instr+1] = (PUNTERO_TABLA_LIBRO >> 8) & 0xFF

_fin_cave_traduccion = 0x34F802 + len(cave)
assert _fin_cave_traduccion <= DIR_TABLA_LIBRO, (
    f"COLISION: el cave de traduccion termina en 0x{_fin_cave_traduccion:06X}, "
    f"se superpone con la tabla del libro en 0x{DIR_TABLA_LIBRO:06X}."
)

# === FIX v21: elimina el destello del primer frame del libro animado
#     (agosto 2026) -- NOP de las dos llamadas de dibujado ===
#
# Ver la entrada "v21" del historial de versiones (arriba, cabecera del
# archivo) y generar_horizontal_compresion_v21.py (rama en espanol) para
# el detalle completo de la investigacion.
#
# Resumen: la rutina de animacion del libro (banco 0x34 offset local
# 0x1BAD, mas espejo en banco 0x74) dibuja el icono llamando DOS veces a
# la funcion de blitting generica (CALL 0x4451D) -- una con el contador
# "viejo" (offset local 0x1BF8) y otra con el contador "nuevo" tras
# calcular el wrap (offset local 0x1C4C). La primera de estas dos
# llamadas se ejecuta SIEMPRE, sin ninguna condicion. Estas dos
# instrucciones son EXCLUSIVAS del dibujado del libro. Reemplazarlas por
# NOP hace que la rutina siga llevando la cuenta del contador
# exactamente igual que antes, pero nunca mas dibuje el icono -- sin
# escribir ni leer ninguna variable de RAM nueva.
_LIBRO_NOP_SITES_LOCAL = [0x1BF8, 0x1C4C]  # offsets locales dentro del banco
_LIBRO_NOP = bytes([0x90, 0x90, 0x90])

for _banco_libro in (0x34, 0x74):
    _base_banco_libro = _banco_libro * 0x10000
    for _site_local_libro in _LIBRO_NOP_SITES_LOCAL:
        _addr_call = _base_banco_libro + _site_local_libro
        _orig3 = bytes(rom[_addr_call:_addr_call + 3])
        assert _orig3[0] == 0xE8, (
            f"FIX v21 (libro animado): byte inesperado en 0x{_addr_call:06X} "
            f"(banco 0x{_banco_libro:02X}): {_orig3.hex()} "
            f"(se esperaba E8 xx xx, CALL rel16). No se aplica el parche.")
        rom[_addr_call:_addr_call + 3] = _LIBRO_NOP

    print(f'FIX v21 (libro animado) aplicado en banco 0x{_banco_libro:02X}: '
          f'{len(_LIBRO_NOP_SITES_LOCAL)} llamadas de dibujado eliminadas '
          f'(offsets locales {[hex(x) for x in _LIBRO_NOP_SITES_LOCAL]})')

# === FIN FIX v21 (libro animado) ===

# === PRUEBA: zereo del libro animado COMBINADO con el redirect de arriba
#     (julio 2026, v18_menutest3) ===
#
# Historial (ver TerrorsWonderSwan/docs/2026-06-27_libro_animado_solucion_v9.md):
# el zereo directo de estos datos (v8) causaba un freeze 100% reproducible
# en la rama alternativa de H2 y en creditos de H1/H2. Investigado en vivo
# con breakpoints: el freeze pasaba porque el puntero 0x09EC (que el motor
# usa para calcular el "total de frames" de la animacion) apuntaba
# ORIGINALMENTE a estos mismos datos del libro -- al leer ceros, el
# calculo se rompia.
#
# Desde entonces, el fix de arriba ya REDIRIGE ese puntero a TABLA_LIBRO
# (datos propios, nunca a esta zona) -- el mecanismo que causaba el
# freeze ya no lee de aca. Por eso esta prueba agrega el zereo de los
# datos originales encima del redirect (no en su lugar): la hipotesis es
# que el freeze ya no deberia reproducirse porque nada deberia estar
# leyendo esta zona. Efecto esperado si la hipotesis es correcta: el
# libro deja de dibujarse desde el primer frame (sin los 1-2 frames de
# animacion visible que quedan con el redirect solo, antes de que el
# contador llegue al valor "fuera de rango").
#
# RIESGO CONOCIDO, sin descartar (ver seccion 4 del doc, "lagunas
# reales"): no esta confirmado al 100% que NINGUN otro codigo del motor
# lea estos datos por un motivo distinto al del contador. Si algo se
# rompe (freeze, grafico corrupto) en cualquier pantalla al probar esto,
# el primer sospechoso es este zereo -- revertir esta seccion sola (sin
# tocar el redirect de arriba) alcanza para volver al estado anterior.
#
# REACTIVADO en v19b (julio 2026): la version anterior (v19) confirmo
# basura grafica INTERMITENTE en H5-P1 incluso con este zereo
# DESACTIVADO -- descartando al zereo como causa (no puede ser, si no
# estaba activo). El glitch parece venir de una condicion de carrera
# entre el fix de navegacion del menu (ES_MENU_ACTUAL, ver
# HOOK_MENU_TRADUCCION.md seccion 7) y el mecanismo del libro cuando
# usa el valor "fuera de rango" del contador (ver comentario en
# TABLA_LIBRO mas arriba). Se reactiva el zereo AHORA junto con valores
# normales en TABLA_LIBRO, como prueba conjunta de que sacar al libro
# del camino de codigo "fuera de rango" (caso limite no entendido del
# todo) elimina la sensibilidad al timing que causaba el glitch.
# REVERTIDO EN v19d (julio 2026): confirmado en vivo (Mesen) que este zereo
# -- combinado con el cambio de TABLA_LIBRO de arriba -- causa un freeze
# reproducible en H5 (P67-69, ruta alterna), no relacionado con ningun banco
# de datos ni con el CSV (se aislo probando con el CSV casi vacio y cambiando
# bancos, sin efecto -- solo revertir estas dos lineas especificas elimino
# el freeze). Esto confirma el riesgo que ya advertia el comentario original
# de esta seccion ("no esta confirmado al 100% que NINGUN otro codigo del
# motor lea estos datos por un motivo distinto al del contador"): algo en la
# ruta alterna de H5 SI lee esta zona por otro motivo. Vuelve a quedar
# desactivado, igual que en v19 -- el glitch grafico intermitente de H5-P1
# que esto intentaba corregir sigue sin resolver, pero un freeze reproducible
# es peor que ese glitch. Nada mas cambio respecto de v19c (menu traducido,
# cave, gates 0x0069/0x0060, zona_chars multibanco, bancos reservados: todo
# igual).
#for _base_libro in (0x2CF000, 0x6CF000):
#    rom[_base_libro:_base_libro+0x1000] = b'\x00' * 0x1000

rom[0x3E0180:0x3E0200] = b'\x00' * 0x80
rom[0x7E0180:0x7E0200] = b'\x00' * 0x80
rom[0x3E0B00:0x3E0B80] = b'\x00' * 0x80
rom[0x7E0B00:0x7E0B80] = b'\x00' * 0x80

# === FIX PUNTUAL: entrada de tabla de bancos en 0xFF370 (julio 2026) ===
#
# Causa raiz encontrada con Mesen (save state H3-P1->P2, banco 0x5E como
# BANCO_TABLA_INDICE): el motor original selecciona banco de ROM a traves
# de una tabla propia en el banco fijo 0xFF370 (indexada por ES:[0x0C90]).
# Esa tabla fue diseñada para la ROM original de 4MB (64 bancos, 6 bits).
# La entrada usada en esta escena (offset CPU $FFA4D, file offset
# 0x3FFA4D/0x7FFA4D) vale 0xA0DE: el byte bajo (0xDE) se usa tal cual como
# numero de banco de 8 bits. En el esquema original de 6 bits ese mismo
# byte hubiera aterrizado en el banco 0x1E (0xDE & 0x3F); con la ROM
# expandida aterriza en 0x5E en cambio, la zona donde vive BANCO_TABLA_INDICE.
#
# PRIMER INTENTO DESCARTADO: angostar la mascara del motor (AND AX,$00FF ->
# AND AX,$003F) en la rutina que consume esta tabla (0x340D81/0x740D81)
# arreglaba este freeze puntual, pero esa rutina es COMPARTIDA -- el mismo
# codigo se usa tambien para leer los bancos de datos del parche
# (0x43/0x44/0x50/0x5E/0x60), asi que angostar la mascara ahi rompia TODA
# la traduccion (confirmado probando: la ROM con esa mascara ya no
# traducia ninguna historia). Se revirtio ese intento.
#
# FIX ACTUAL: en vez de tocar el mecanismo de seleccion de banco (que es
# generico y compartido), se corrige el byte malo directamente en la
# tabla de origen -- solo esa entrada especifica, sin tocar la mascara ni
# ningun otro banco. 0xDE -> 0x1E (banco original correcto para este
# indice de tabla).
#
# Pendiente de validar contra el resto de BANCOS_PROHIBIDOS -- este fix
# cubre unicamente la entrada de tabla usada en H3-P2. Si el mismo tipo de
# freeze aparece en otro punto, hay que ubicar SU entrada de tabla
# especifica (offset CPU distinto, mismo mecanismo) y corregirla igual,
# sin reutilizar estas direcciones.
for base_tabla_banco in [0x3FFA4D, 0x7FFA4D]:
    assert rom[base_tabla_banco] == 0xDE, (
        f"Byte inesperado en 0x{base_tabla_banco:06X}: "
        f"{rom[base_tabla_banco]:02X} (se esperaba DE)"
    )
    rom[base_tabla_banco] = 0x1E

# === FIX PUNTUAL 2: entrada de tabla de bancos en 0xFF882 (julio 2026) ===
#
# Mismo mecanismo que el fix anterior (0xFFA4D), pero para un freeze
# distinto: H1-P149 (ruta no mapeada previamente), causado por el banco
# 0x50 (en uso activo como banco de datos en varias historias).
#
# Diagnosticado en vivo con Mesen (save H1_save_P148.mss, avanzar dos
# veces con el mismo ROM usando banco 0x50 -> se congela con corrupcion
# grafica identica al patron de H3-P2, seguida de "colgado" sirviendo
# solo IRQs de sonido/vblank). Con breakpoint condicional en escritura a
# puerto $C3 (value == $D0) se confirmo en vivo: la rutina compartida de
# seleccion de banco (misma de siempre, 0x340D61-0x340D8D/espejo) lee la
# tabla en el banco fijo 0xFF370 con BX=$0512 (ES:[0x0C90]=0x01B0*3),
# es decir offset CPU $FF882 (file offset 0x3FF882/0x7FF882), valor
# 0xD0. Con mascara efectiva de 7 bits (0xD0 & 0x7F = 0x50) esto colisiona
# con el banco de datos 0x50. En el esquema original de 6 bits ese mismo
# byte hubiera aterrizado en el banco 0x10 (0xD0 & 0x3F).
#
# FIX: igual que el anterior, se corrige solo el byte malo en la tabla de
# origen, sin tocar la mascara ni el mecanismo compartido. 0xD0 -> 0x10.
for base_tabla_banco2 in [0x3FF882, 0x7FF882]:
    assert rom[base_tabla_banco2] == 0xD0, (
        f"Byte inesperado en 0x{base_tabla_banco2:06X}: "
        f"{rom[base_tabla_banco2]:02X} (se esperaba D0)"
    )
    rom[base_tabla_banco2] = 0x10

# === FIX PUNTUAL 3: entrada de tabla de bancos en 0xFFC3C -- banco 0x6C (julio 2026) ===
#
# Mismo mecanismo que los dos fixes anteriores, para un tercer freeze
# distinto: H1-P160 (un par de pantallas despues de H1-P149, en la misma
# ruta; save de prueba: prueba1.mss, carpeta save_H1), causado por el
# banco 0x6C.
#
# Diagnosticado en vivo con Mesen (save prueba1.mss = H1-P160, se congela
# al avanzar el dialogo una sola vez con "s"). Con breakpoint de ejecucion en la
# rutina compartida de despacho de banco ($40D88, la misma de siempre) se
# capturo en vivo: AX=$00EC, BX=$08CC, DS=$FF37 en el momento del
# `OUT $C3,AL`. Direccion fisica de la entrada de tabla: DS*16+BX =
# $FF370+$08CC = $FFC3C (file offset 0x3FFC3C/0x7FFC3C), valor 0xEC.
# Con mascara efectiva de 7 bits (0xEC & 0x7F = 0x6C) esto colisiona con
# el banco de datos 0x6C. En el esquema original de 6 bits ese mismo byte
# hubiera aterrizado en el banco 0x2C (0xEC & 0x3F).
#
# Confirmado end-to-end: tras el OUT con AL=$EC, la ejecucion sigue la
# misma cadena de corrupcion ya conocida ($4093F -> $44669 -> $446E7 ->
# $4473F "MOV ES:[DI],DX" con ES=0000,DI=0000), escribiendo sobre la
# tabla de vectores de interrupcion (fisico $000000) -- exactamente el
# mismo patron de H1-P149, confirmado con breakpoint de escritura en
# $000000-$0003FF.
#
# FIX: igual que los anteriores, se corrige solo el byte malo en la tabla
# de origen, sin tocar la mascara ni el mecanismo compartido. 0xEC -> 0x2C.
for base_tabla_banco3 in [0x3FFC3C, 0x7FFC3C]:
    assert rom[base_tabla_banco3] == 0xEC, (
        f"Byte inesperado en 0x{base_tabla_banco3:06X}: "
        f"{rom[base_tabla_banco3]:02X} (se esperaba EC)"
    )
    rom[base_tabla_banco3] = 0x2C

# === FIX PUNTUAL 4: entrada de tabla de bancos en 0xFFC4B -- banco 0x59 (julio 2026) ===
#
# El freeze de H1-P160 (save prueba1.mss) resulto tener DOS entradas de
# tabla malas para la misma escena, no una sola -- el motor pasa por
# ambas en la misma secuencia de dialogo. El FIX PUNTUAL 3 (0xFFC3C,
# banco 0x6C) era necesario pero no suficiente: tras aplicarlo, el
# freeze persistia. Re-diagnosticando con Mesen (mismo save prueba1.mss,
# breakpoint de ejecucion en $40D88 con condicion "AX != $2C" para saltar
# los llamados benignos ya corregidos) se encontro una segunda entrada
# real: BX=$08DB, DS=$FF37 -> direccion fisica $FFC4B (file offset
# 0x3FFC4B/0x7FFC4B), valor 0xD9.
#
# Con mascara de 7 bits (0xD9 & 0x7F = 0x59) esto colisiona con el banco
# 0x59 -- que YA estaba en BANCOS_PROHIBIDOS ("congela H1 al inicio"),
# confirmando que es el mismo mecanismo. Banco original de 6 bits:
# 0xD9 & 0x3F = 0x19.
#
# Confirmado end-to-end igual que los anteriores: tras el OUT con AL=$D9,
# la ejecucion cae en la misma cadena de corrupcion conocida ($4093F ->
# $44669 -> $446E7 -> $4473F "MOV ES:[DI],DX" con ES=0000,DI=0000).
#
# LECCION: una misma escena/freeze puede depender de MAS DE UNA entrada
# de tabla mala. Al diagnosticar un freeze nuevo, no alcanza con corregir
# la primera entrada encontrada y dar por cerrado el caso -- hay que
# volver a probar el save state con el fix aplicado, y si el freeze
# persiste, repetir el procedimiento de diagnostico desde ahi.
for base_tabla_banco4 in [0x3FFC4B, 0x7FFC4B]:
    assert rom[base_tabla_banco4] == 0xD9, (
        f"Byte inesperado en 0x{base_tabla_banco4:06X}: "
        f"{rom[base_tabla_banco4]:02X} (se esperaba D9)"
    )
    rom[base_tabla_banco4] = 0x19

# === FIX PUNTUAL 5: entrada de tabla de bancos en 0xFF888 -- banco 0x50 (julio 2026) ===
#
# El freeze de H1-P160 (save prueba1.mss) seguia persistiendo incluso con
# los FIX 3 (banco 0x6C) y FIX 4 (banco 0x59) aplicados. El usuario
# confirmo empiricamente (diagnostico_bancos.py, marcando/desmarcando
# 0x50 como prohibido) que el banco causante es el 0x50 -- el mismo
# banco de H1-P149 (FIX PUNTUAL 2), pero NO la misma entrada de tabla:
# el FIX PUNTUAL 2 corrige $FF882, y esta escena (H1-P160) usa una
# entrada DISTINTA de la tabla, 6 bytes mas adelante (2 entradas de 3
# bytes despues).
#
# Re-diagnosticado con Mesen (mismo save prueba1.mss, breakpoint de
# ejecucion en $40D88 con condicion "AX == $D0 || AX == $50" para saltar
# directo a un match real) se encontro: DS=$FF37, BX=$0518 -> direccion
# fisica $FF888 (file offset 0x3FF888/0x7FF888), valor 0xD0 -- el MISMO
# byte que $FF882, pero en una entrada de tabla distinta. Confirmado
# end-to-end: tras el OUT con AL=$D0, la ejecucion cae en la misma cadena
# de corrupcion conocida ($4093F -> $44669 -> $446E7 -> $4473F).
#
# Con mascara de 7 bits (0xD0 & 0x7F = 0x50) colisiona con el banco de
# datos 0x50. Banco original de 6 bits: 0xD0 & 0x3F = 0x10.
#
# LECCION (refuerza la del FIX 4): un mismo banco problematico (0x50)
# puede tener VARIAS entradas de tabla distintas que lo referencian mal,
# en escenas distintas. Corregir una entrada no cubre las demas -- cada
# freeze nuevo hay que re-diagnosticarlo aunque el banco resulte ser uno
# ya visto antes.
for base_tabla_banco5 in [0x3FF888, 0x7FF888]:
    assert rom[base_tabla_banco5] == 0xD0, (
        f"Byte inesperado en 0x{base_tabla_banco5:06X}: "
        f"{rom[base_tabla_banco5]:02X} (se esperaba D0)"
    )
    rom[base_tabla_banco5] = 0x10

# === HISTORIA DEL FIX GLOBAL (julio 2026) -- primer intento descartado,
#     version correcta SI implementada (ver cave, comentario "FIX GLOBAL") ===
#
# Los 5 fixes puntuales de arriba corrigen, uno por uno, bytes especificos
# de una tabla legacy en el banco fijo $FF370 (indexada por ES:[0x0C90],
# entradas de 3 bytes: word + banco). Cada uno se encontro jugando una
# ruta nueva, lo cual era insostenible: agregar una traduccion a un banco
# nuevo puede chocar con una entrada de tabla nunca antes visitada.
#
# Primer intento (descartado): desensamblando la rutina compartida
# ($340D61-$340D8D, con capstone sobre Terrors_Espejo_Puro.ws) se encontro
# que en 340D81 hay "AND AX, 0x00FF" justo antes del OUT final (340D88),
# que solo separa el byte bajo del word leido de la tabla, sin limitar su
# rango a 6 bits (ese limite vivia en el hardware del mapper original, no
# en este codigo). La idea era angostarla a "AND AX,0x003F" para simular
# el hardware original y corregir todas las entradas de la tabla de una
# vez, sin tener que jugar cada ruta.
#
# DESCARTADO (ese intento puntual en 0x340D81): angostar esa mascara
# compartida rompe TODA la traduccion. Motivo: nuestro cave se activa con
# "CMP AX,0x00FE / JE .es_kanji" en cave_start, usando este MISMO AX (el
# CALL a nuestro cave esta empalmado justo despues de la mascara, en el
# lugar de la antigua instruccion "MOV ES:[0xC94],AX"). Con mascara de 6
# bits, 0xFE & 0x3F = 0x3E -- nunca puede volver a valer 0xFE, asi que el
# cave nunca se dispara y no traduce nada. Esto confirma una nota de una
# sesion anterior que ya habia encontrado este mismo problema al intentar
# lo mismo.
#
# FIX CORRECTO -- IMPLEMENTADO: angostar el banco SOLO para el OUT final
# en 0x340D88, sin tocar el AX que ve el cave en su propio chequeo de
# entrada. Se agrego "and al, 0x3F" dentro del propio cave, justo antes
# de restaurar registros y hacer RET, dejando 0x340D81 sin tocar (0x00FF).
# Ver el epilogo ".fin" del cave mas abajo (comentario "FIX GLOBAL (julio
# 2026)") para el detalle y la direccion exacta.
#
# Validado en vivo: caso original H1C-P184/banco 0x51 (freeze en save
# H1_save_P183.mss) dejo de congelar, y se jugo la ruta H1C completa sin
# freezes, incluyendo un caso adicional (banco 0x52) que tambien fallaba
# antes del fix. Los 5 fixes puntuales de arriba se dejan intactos por
# compatibilidad/documentacion historica, pero ya no son necesarios para
# casos nuevos: el fix global cubre toda la tabla de una sola vez.


# ------------------------------------------------------------------------
# === MECANISMO DE BORRADO DEL MENU (v19c) ===
# Parche adicional sobre bancos 0x34/0x74, separado del cave (0x4F802) y
# de la tabla del libro (0x34FE00) -- no toca ninguno de los dos.
#
# PROBLEMA que resuelve: la rutina de dibujado nativa del juego redibuja
# el kanji original del menu en cada refresco de pantalla, sin saber que
# el cave ya escribio texto traducido en esa misma posicion -- lo tapa de
# nuevo cada vez.
#
# MECANISMO (3 puntos de enganche en banco 0x34/0x74):
#  1) HOOK1 -- offset local 0x3F84, "MOV DI, ES:[0xC92]" (5 bytes, unica).
#     Es un NO-OP puro en v19c: repite la instruccion original que
#     reemplazo y vuelve, sin tocar RAM. (Historial: en v19/v19b escribia
#     un flag en WRAM 0x0DB4 para "avisarle" al cave que se estaba
#     dibujando el menu -- ver nota "MECANISMO ABANDONADO" mas abajo.)
#  2) HOOKCAP -- offset local 0x40FD, "CMP WORD ES:[0xC76],1" (6 bytes,
#     unica, justo antes del branch que decide como se dibuja). Chequea
#     DIRECTAMENTE es:[0x09D6]==0 (0 durante el menu, valor de historia
#     -- no cero -- durante narrativa, ver mas abajo). Si es 0, guarda el
#     contenido ACTUAL de ES:[SI-0x20]/ES:[SI-0x10]/ES:[SI] en WRAM
#     (0x0DB6 en adelante) antes de que el motor los modifique. Si no,
#     no hace nada (deja pasar el dibujado nativo tal cual).
#  3) HOOKRES -- offset local 0x413E, "POP CX" + "ADD WORD ES:[0xC84],2"
#     (7 bytes, punto de convergencia de las dos ramas de dibujado). Mismo
#     chequeo que HOOKCAP: si es:[0x09D6]==0, restaura los 3 words
#     guardados por HOOKCAP, deshaciendo el redibujado de este frame.
#
# QUE ES es:[0x09D6]: se escribe en UN SOLO lugar de todo el juego (banco
# 0x34, offset local 0x13B0), una funcion que corre al entrar a una
# historia: lee es:[0x9D8] (indice de historia activa, 0=H1..5=H6),
# busca ese indice en una tabla fija de 7 entradas (banco 0x34, offset
# 0x11C0: H1=0x02F3, H2=0x02F2, H3=0x02F7, H4=0x02F4, H5=0x02F6,
# H6=0x02F8) y guarda el valor encontrado en es:[0x9D6]. Antes de entrar
# a cualquier historia (o sea, en el menu recien iniciado) nunca se
# escribe, asi que queda en su valor inicial 0x0000 -- confirmado
# empiricamente por el usuario via Mesen (Work RAM) en el menu y durante
# varias historias.
#
# LIMITACION CONOCIDA (sin resolver): es:[0x09D6] NUNCA se resetea a 0 al
# volver a una pantalla de menu sin salir realmente de la historia activa
# (confirmado con la opcion "insertar marcador" del menu de pausa: vuelve
# a mostrar una pantalla de menu, pero es:[0x9D8] -- y por lo tanto
# es:[0x9D6] -- se queda con el valor de la historia en curso). En ese
# caso puntual el borrado no se activa y el japones original reaparece.
# Pendiente: ubicar el codigo que dispara esa pantalla especifica y
# forzar ahi un es:[0x9D6]=0.
#
# MECANISMO ABANDONADO (v19/v19b, ya NO esta en el codigo): antes, HOOK1
# escribia un flag en WRAM (0x0DB4) que el CAVE leia (o que HOOKCAP/
# HOOKRES chequeaban) para decidir cuando borrar. Se abandono porque el
# cave dispara con mucha menos frecuencia que la rutina de dibujado
# nativa -- cualquier bandera intermedia quedaba expuesta a problemas de
# timing entre ambos (se probaron variantes con una lista fija de kanjis
# del menu y con es:[0x09D4]/es:[0x09D6] leidos DESDE EL CAVE -- ninguna
# lograba activar el borrado de forma confiable). Chequear DENTRO de
# HOOKCAP/HOOKRES, en el mismo punto donde se dibuja, elimina ese
# problema de raiz.
# ------------------------------------------------------------------------

HOOK1_SITE_LOCAL    = 0x3F84
HOOK1_RETURN_LOCAL  = 0x3F89
HOOKCAP_SITE_LOCAL   = 0x40FD
HOOKCAP_RETURN_LOCAL = 0x4103
HOOKRES_SITE_LOCAL   = 0x413E
HOOKRES_RETURN_LOCAL = 0x4145
STUB_BASE_LOCAL     = 0xFE03
STUB1_ADDR_LOCAL    = 0xFE03
STUBCAP_ADDR_LOCAL  = 0xFE65
STUBRES_ADDR_LOCAL  = 0xFE93
STUB_END_LOCAL      = 0xFEC0
DIR_CHEQUEO_HISTORIA = 0x09D6  # 0 en el menu, valor de historia durante narrativa

HOOK1_PATCH_BYTES   = bytes.fromhex('e97cbe9090')    # 5 bytes
HOOKCAP_PATCH_BYTES = bytes.fromhex('e965bd909090')  # 6 bytes
HOOKRES_PATCH_BYTES = bytes.fromhex('e952bd90909090')  # 7 bytes
STUB1_BYTES   = bytes.fromhex('268b3e920ce97e419090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090909090')
STUBCAP_BYTES = bytes.fromhex('501e31c08ed8a1d60909c07514268b44e0a3b60d268b44f0a3b80d268b04a3ba0d1f58e978429090909090909090')
STUBRES_BYTES = bytes.fromhex('59501e31c08ed8a1d60909c07514a1b60d268944e0a1b80d268944f0a1ba0d2689041f58268306840c02e98542')
# STUBCAP/STUBRES: push ax/ds; ds=0; mov ax,[0x9D6]; or ax,ax; jne skip ->
# capturar/restaurar (misma logica que la base "antigravity", incondicional,
# solo que ahora envuelta en este chequeo) -> skip: pop ds/ax; jmp de vuelta.
# Ensamblado a mano y verificado con capstone (offsets/saltos correctos,
# entra justo en el espacio libre de los stubs).

_ORIG_HOOK1   = bytes.fromhex('268b3e920c')
_ORIG_HOOKCAP = bytes.fromhex('26833e760c01')
_ORIG_HOOKRES = bytes.fromhex('59268306840c02')

for _banco_menu in (0x34, 0x74):
    _base_banco = _banco_menu * 0x10000
    _addr_h1  = _base_banco + HOOK1_SITE_LOCAL
    _addr_cap = _base_banco + HOOKCAP_SITE_LOCAL
    _addr_res = _base_banco + HOOKRES_SITE_LOCAL
    _addr_stub_base = _base_banco + STUB_BASE_LOCAL

    _actual_h1 = bytes(rom[_addr_h1:_addr_h1 + len(_ORIG_HOOK1)])
    assert _actual_h1 == _ORIG_HOOK1, (
        f"HOOK1 (borrado menu v19c): bytes inesperados en 0x{_addr_h1:06X} "
        f"(banco 0x{_banco_menu:02X}): {_actual_h1.hex()} "
        f"(se esperaba {_ORIG_HOOK1.hex()}). No se aplica el parche.")
    _actual_cap = bytes(rom[_addr_cap:_addr_cap + len(_ORIG_HOOKCAP)])
    assert _actual_cap == _ORIG_HOOKCAP, (
        f"HOOKCAP (borrado menu v19c): bytes inesperados en 0x{_addr_cap:06X} "
        f"(banco 0x{_banco_menu:02X}): {_actual_cap.hex()} "
        f"(se esperaba {_ORIG_HOOKCAP.hex()}). No se aplica el parche.")
    _actual_res = bytes(rom[_addr_res:_addr_res + len(_ORIG_HOOKRES)])
    assert _actual_res == _ORIG_HOOKRES, (
        f"HOOKRES (borrado menu v19c): bytes inesperados en 0x{_addr_res:06X} "
        f"(banco 0x{_banco_menu:02X}): {_actual_res.hex()} "
        f"(se esperaba {_ORIG_HOOKRES.hex()}). No se aplica el parche.")

    _region_stub = bytes(rom[_addr_stub_base:_addr_stub_base + (STUB_END_LOCAL - STUB_BASE_LOCAL)])
    assert _region_stub == b'\xff' * len(_region_stub), (
        f"HOOK borrado menu v19c: la zona libre esperada en 0x{_addr_stub_base:06X}-"
        f"0x{_addr_stub_base + len(_region_stub):06X} (banco 0x{_banco_menu:02X}) "
        f"no esta completamente en 0xFF -- posible colision. No se aplica el parche.")

    rom[_addr_h1:_addr_h1 + len(HOOK1_PATCH_BYTES)] = HOOK1_PATCH_BYTES
    rom[_addr_cap:_addr_cap + len(HOOKCAP_PATCH_BYTES)] = HOOKCAP_PATCH_BYTES
    rom[_addr_res:_addr_res + len(HOOKRES_PATCH_BYTES)] = HOOKRES_PATCH_BYTES

    _addr_stub1   = _base_banco + STUB1_ADDR_LOCAL
    _addr_stubcap = _base_banco + STUBCAP_ADDR_LOCAL
    _addr_stubres = _base_banco + STUBRES_ADDR_LOCAL
    rom[_addr_stub1:_addr_stub1 + len(STUB1_BYTES)] = STUB1_BYTES
    rom[_addr_stubcap:_addr_stubcap + len(STUBCAP_BYTES)] = STUBCAP_BYTES
    rom[_addr_stubres:_addr_stubres + len(STUBRES_BYTES)] = STUBRES_BYTES

    print(f'Parche de borrado del menu (v19c) aplicado en banco 0x{_banco_menu:02X}: '
          f'hook1@0x{HOOK1_SITE_LOCAL:04X}, hookcap@0x{HOOKCAP_SITE_LOCAL:04X}, '
          f'hookres@0x{HOOKRES_SITE_LOCAL:04X}, stub 0x{STUB_BASE_LOCAL:04X}-0x{STUB_END_LOCAL:04X}')

# === FIN MECANISMO DE BORRADO DEL MENU (v19c) ===
# ------------------------------------------------------------------------

# ------------------------------------------------------------------------
# === FIX GLOBAL SONIDO (agosto 2026) ===
#
# Elimina el glitch de audio intermitente ("pitidos"). Ver el docstring de
# cabecera (entrada "v20") para el resumen de la investigacion completa, y
# "CONTEXTO_GLITCH_SONIDO_2026-08-08_HANDOFF.md" para el detalle extendido.
#
# Causa raiz: 7 rutinas del motor original (banco 0x34, mas 7 espejos en
# banco 0x74) leen la envolvente de volumen de sonido desde un banco de ROM
# seleccionado por el puerto $C2 (IO_BANK_ROM0), sacando el numero de banco
# directo del byte bajo de una celda de WRAM (es:[0x0BB2..0x0BBA], variable
# segun el sitio) SIN NINGUNA MASCARA. Con la ROM expandida, ese byte puede
# aterrizar en los bancos 0x43-0x61 (fuente/tablas de traduccion) en vez de
# quedarse en el rango original de 6 bits (0-0x3F), y el motor termina
# mandando esos datos -- que no son de sonido -- al registro de volumen del
# canal (puerto $89), produciendo el pitido.
#
# Cada sitio tiene el patron de 6 bytes "26 A1 xx 0B E6 C2"
# (MOV AX,ES:[$0Bxx] / OUT $C2,AL). Localizados por busqueda binaria del
# opcode E6 C2 en Terrors_compresion.ws (agosto 2026):
#   banco 0x34 (offsets locales, identicos en banco 0x74):
#   0x0F93, 0x0FF9, 0x5240, 0x55ED, 0x5842, 0x598E, 0x5A0D
#
# FIX (mismo criterio que el FIX GLOBAL de julio 2026 para el puerto $C3):
# enmascarar con "AND AL,0x3F" justo antes de cada OUT $C2,AL, replicando
# el hardware original de 6 bits, SIN mover ningun banco ni dato. Como son
# 14 sitios dentro del motor original (sin espacio libre junto a cada uno
# para insertar la mascara in-line), se usa la tecnica de trampolin: cada
# sitio se reemplaza por un JMP near de 3 bytes hacia un trampolin en la
# zona libre al final del banco (0xFEC0 en adelante -- justo despues de
# donde terminan los stubs del borrado de menu de arriba, sin colision).
# El trampolin re-ejecuta la carga de WRAM, aplica la mascara, hace el OUT
# y vuelve al flujo original.
#
# Validado en vivo por el usuario escuchando los creditos completos con la
# ROM parchada (Terrors_diag_maskC2.ws): "ya no se oyen los pitidos".
_SND_ENVELOPE_SITES_LOCAL = [0x0F93, 0x0FF9, 0x5240, 0x55ED, 0x5842, 0x598E, 0x5A0D]
_SND_TRAMPOLINE_BASE_LOCAL = 0xFEC0  # zona libre, justo tras el stub de borrado de menu

for _banco_snd in (0x34, 0x74):
    _base_banco_snd = _banco_snd * 0x10000
    _tramp_cursor = _SND_TRAMPOLINE_BASE_LOCAL
    for _site_local in _SND_ENVELOPE_SITES_LOCAL:
        _addr_site = _base_banco_snd + _site_local
        _orig6 = bytes(rom[_addr_site:_addr_site + 6])
        assert (_orig6[0] == 0x26 and _orig6[1] == 0xA1 and _orig6[3] == 0x0B
                and _orig6[4] == 0xE6 and _orig6[5] == 0xC2), (
            f"FIX GLOBAL SONIDO: patron inesperado en 0x{_addr_site:06X} "
            f"(banco 0x{_banco_snd:02X}): {_orig6.hex()} "
            f"(se esperaba 26 A1 xx 0B E6 C2). No se aplica el parche.")
        _wram_ptr_lo = _orig6[2]

        _addr_tramp = _base_banco_snd + _tramp_cursor
        _region_libre = bytes(rom[_addr_tramp:_addr_tramp + 11])
        assert _region_libre == b'\xff' * len(_region_libre), (
            f"FIX GLOBAL SONIDO: zona de trampolin no esta libre en "
            f"0x{_addr_tramp:06X} (banco 0x{_banco_snd:02X}): "
            f"{_region_libre.hex()} -- posible colision. No se aplica el parche.")

        # JMP near desde el sitio original hacia el trampolin (3 bytes).
        _rel_to_tramp = (_addr_tramp - (_addr_site + 3)) & 0xFFFF
        rom[_addr_site] = 0xE9
        rom[_addr_site + 1] = _rel_to_tramp & 0xFF
        rom[_addr_site + 2] = (_rel_to_tramp >> 8) & 0xFF
        # _addr_site+3..+5 (0B E6 C2 originales) quedan como bytes muertos:
        # el JMP los salta, nunca se ejecutan.

        # Trampolin: re-ejecuta la carga, aplica la mascara, hace el OUT y vuelve.
        _tramp_bytes = bytearray()
        _tramp_bytes += bytes([0x26, 0xA1, _wram_ptr_lo, 0x0B])  # MOV AX, ES:[$0Bxx]
        _tramp_bytes += bytes([0x24, 0x3F])                       # AND AL, 0x3F  <- LA MASCARA
        _tramp_bytes += bytes([0xE6, 0xC2])                       # OUT 0xC2, AL
        _back_addr = _addr_site + 6
        _rel_back = (_back_addr - (_addr_tramp + len(_tramp_bytes) + 3)) & 0xFFFF
        _tramp_bytes += bytes([0xE9, _rel_back & 0xFF, (_rel_back >> 8) & 0xFF])

        rom[_addr_tramp:_addr_tramp + len(_tramp_bytes)] = _tramp_bytes
        _tramp_cursor += len(_tramp_bytes)

    print(f'FIX GLOBAL SONIDO aplicado en banco 0x{_banco_snd:02X}: '
          f'{len(_SND_ENVELOPE_SITES_LOCAL)} sitios, '
          f'trampolines 0x{_SND_TRAMPOLINE_BASE_LOCAL:04X}-0x{_tramp_cursor:04X}')

# === FIN FIX GLOBAL SONIDO (agosto 2026) ===
# ------------------------------------------------------------------------

open(ROM_OUTPUT, 'wb').write(rom)
print(f'ROM generada: {ROM_OUTPUT}')
