; cave_en.asm
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

BANCO_FUENTE    equ 0x60
BANCO_TABLAS    equ 0x40
N_PANT          equ 4058
FLAG_COMPRIMIDO equ 0x8000
DELTA_TILESET   equ 0x0100   ; incremento tileset_addr entre letras consecutivas

; v22: tablas auxiliares de busqueda (ver "Construir TABLA_A / TABLA_B" en
; el Python). BANCO_TABLA_OPT es un banco NUEVO, separado de BANCO_TABLAS
; (pant_tabla no se toco). Todos los offsets son bytes dentro de ese banco.
BANCO_TABLA_OPT   equ 0x41
N_TABLA_A         equ 3
TABLA_A_INDEX_OFF equ 0x0000
TABLA_A_ROWS_OFF  equ 0x0012
N_TABLA_B         equ 7495
TABLA_B_OFF       equ 0x001E

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
