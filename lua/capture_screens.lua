-- capture_screens.lua
--
-- VARIANTE de explorador_autoavance_v1.lua para AUDITORIA de "segunda vuelta":
-- el usuario noto que al reiniciar una historia ya completada (entrar por un
-- libro/save y elegir "reiniciar historia"), algunas pantallas muestran texto
-- DISTINTO al de la primera vez, aunque el juego las considere "la misma
-- pantalla" en la secuencia. El chequeo de es:[0x0CF0] no alcanza para
-- detectar esto: si dos textos distintos comparten el mismo codigo de kanji/
-- offset, el cave puede mostrar la traduccion de UNO de los dos en ambos
-- casos, marcando "traducido" incluso cuando el texto mostrado no corresponde.
--
-- METODOLOGIA (decidida con el usuario): correr este script UNA VEZ sobre
-- una historia completa empezando de CERO (sin ningun save/eeprom, borrado a
-- mano antes de arrancar), y otra vez sobre la MISMA historia y las MISMAS
-- decisiones (todo opcion 1) pero entrando por "reiniciar historia" desde un
-- libro ya completado. Si el primer_kanji/ultimo_kanji de una pantalla N
-- coincide en ambas corridas, el texto es el mismo -- no hace falta revisar
-- mas. Si difiere, hay que mirar la foto de esa pantalla en ambas corridas
-- (y comparar contra lo que ya esta traducido en el CSV) para saber si de
-- verdad cambio el contenido o es un caso de mismo-texto-distinto-puntero.
--
-- UNICA DIFERENCIA respecto a explorador_autoavance_v1.lua: se guarda una
-- captura de CADA pantalla (traducida o no), no solo las "sin traducir".
-- El nombre de archivo ahora indica el estado (TRADUCIDO_ o SIN_TRADUCIR_)
-- para poder distinguirlas de un vistazo, aunque el CSV ya trae esa columna
-- tambien. Todo lo demas (deteccion por modo 7, botones, preguntas, CSV con
-- historia/primer_kanji/ultimo_kanji, saves .mss) es identico a v1.
--
-- CAMBIO (agosto 2026): BASE_DIR ya NO es una carpeta fija -- se arma con el
-- nombre de la ruta activa (P.ej. [activo] historia=H2G en capture_config.ini
-- -> carpeta "H2G"), dentro de la carpeta CARPETA_RUTAS_BASE (ver SETTINGS mas abajo), en
-- vez de la carpeta de Mesen sobre OneDrive. Motivo: la sincronizacion de
-- OneDrive agregaba latencia a cada operacion de archivo, suficiente para
-- superar el limite de 1 segundo por llamada que impone Mesen a los scripts
-- Lua (confirmado en vivo: "Maximum execution time exceeded" en
-- asegurar_carpeta_saves()). Ademas, si la carpeta de esa ruta YA EXISTE
-- (ej. corriste H2G antes y no renombraste esa carpeta todavia), el script
-- se niega a arrancar en vez de sobreescribir la corrida anterior -- hay que
-- renombrar la carpeta vieja a mano (ej. H2G-01) antes de volver a correr la
-- misma ruta.
--
-- CONTROLES: igual que v1 -- F2 = iniciar/reanudar, F8 = pausar + volcar log.

-- >>> SETTINGS: edit these two paths for your PC (use double backslashes on Windows) <<<
-- Folder where the captures of each route are written (one subfolder per route):
local CARPETA_RUTAS_BASE = "C:\\Terrors\\captures\\"
local SAVES_SUBDIR = "explorador_saves\\"
-- Full path of capture_config.ini (the config file that sits next to this script):
local CONFIG_FILE = "C:\\Terrors\\lua\\capture_config.ini"

-- Lee SOLO el "historia=" de la seccion [activo] -- version minima e
-- independiente de cargar_rutas() (mas abajo), porque BASE_DIR tiene que
-- quedar listo ANTES de esa funcion (MAPEO_FILE, etc. la necesitan ya).
local function leer_historia_activa_minimo()
    local f = io.open(CONFIG_FILE, "r")
    if not f then return nil end
    local en_activo = false
    for linea_raw in f:lines() do
        local linea = linea_raw:match("^%s*(.-)%s*$")
        local pos_comentario = linea:find(";")
        if pos_comentario then linea = linea:sub(1, pos_comentario - 1):match("^%s*(.-)%s*$") end
        local seccion = linea:match("^%[(.-)%]$")
        if seccion then
            en_activo = (seccion == "activo")
        elseif en_activo and linea ~= "" then
            local clave, valor = linea:match("^([%w_]+)%s*=%s*(.-)%s*$")
            if clave == "historia" then
                f:close()
                return valor
            end
        end
    end
    f:close()
    return nil
end

local HISTORIA_ACTIVA_RUTA = leer_historia_activa_minimo()
if not HISTORIA_ACTIVA_RUTA or HISTORIA_ACTIVA_RUTA == "" then
    error("No se pudo leer 'historia=' de la seccion [activo] en " .. CONFIG_FILE
        .. " -- no se puede determinar el nombre de carpeta de esta corrida. Revisa el ini.")
end

local BASE_DIR = CARPETA_RUTAS_BASE .. HISTORIA_ACTIVA_RUTA .. "\\"

-- CAMBIO (agosto 2026, segunda vuelta): abandonado el enfoque con
-- os.execute() por completo -- confirmado en vivo (con reinicio de PC de
-- por medio, asi que no es algo transitorio) que CUALQUIER os.execute()
-- en esta maquina tarda lo suficiente (probablemente antivirus escaneando
-- cada proceso cmd.exe nuevo) como para superar el limite de 1 segundo de
-- Mesen, sin importar cuantas veces se lo llame. Nuevo enfoque: la carpeta
-- de la ruta (ej. E:\...\LUA AUTOMATICO\H2G\) la crea el USUARIO A MANO
-- antes de correr el script (vacia). El Lua NUNCA crea carpetas -- solo
-- chequea/escribe un archivo marcador adentro con io.open (nunca abre un
-- proceso, practicamente instantaneo):
--   - Si el marcador YA existe -> esa carpeta ya se uso, frenar.
--   - Si no se puede ABRIR NI PARA LEER NI PARA ESCRIBIR el marcador ->
--     lo mas probable es que la carpeta en si no exista todavia (el
--     usuario se olvido de crearla) -- frenar con un mensaje claro.
--   - Si se puede escribir -> se escribe el marcador y se sigue normal.
local MARCADOR_CARPETA = BASE_DIR .. "_corrida_iniciada.marker"

local f_marcador_lectura = io.open(MARCADOR_CARPETA, "r")
if f_marcador_lectura then
    f_marcador_lectura:close()
    error("Ya existe el marcador " .. MARCADOR_CARPETA .. " -- esta carpeta ya se uso en una "
        .. "corrida anterior de la ruta " .. HISTORIA_ACTIVA_RUTA .. ". Renombrala a mano "
        .. "(ej. " .. HISTORIA_ACTIVA_RUTA .. "-01) y crea una carpeta " .. HISTORIA_ACTIVA_RUTA
        .. " vacia nueva antes de volver a correr el script. Script detenido.")
end

local f_marcador_escritura = io.open(MARCADOR_CARPETA, "wb")
if not f_marcador_escritura then
    error("No se pudo crear " .. MARCADOR_CARPETA .. " -- lo mas probable es que la carpeta "
        .. BASE_DIR .. " todavia no exista. Creala vacia a mano antes de correr el script. "
        .. "Script detenido.")
end
f_marcador_escritura:write("Corrida iniciada: " .. os.date() .. " -- ruta " .. HISTORIA_ACTIVA_RUTA)
f_marcador_escritura:close()

local MAPEO_FILE = BASE_DIR .. "mapa_rutas_detectadas.txt"

local BOTON_AVANCE = "down"
local BOTON_ARRIBA = "up2"

local FRAMES_SILENCIO_SIN_TEXTO = 600
-- FIX (stall en pantallas de PREGUNTA): el modo 7 (libro animado) NUNCA se
-- activa en una pregunta -- no hay "libro" al final, el juego directamente
-- espera el input del cursor. Ademas, el cursor parpadeante de la pregunta
-- dispara on_exec() todo el tiempo, lo cual resetea frames_desde_ultimo_exec
-- en cada frame -- por eso la red de seguridad de FRAMES_SILENCIO_SIN_TEXTO
-- tampoco llega a cumplirse nunca y el script se queda esperando para
-- siempre (solo avanzaba si el usuario tocaba el boton a mano). Se cuenta
-- un umbral aparte, independiente del silencio del hook, desde el momento
-- en que se detecta la pregunta (las opciones aparecen de una sola vez, sin
-- animacion de dibujado progresivo, asi que un umbral corto y fijo no es
-- una calibracion por pantalla como las que se descartaron para el texto).
local FRAMES_LISTO_PREGUNTA = 30
local FRAMES_PRESION = 6
local FRAMES_PAUSA_ENTRE_BOTONES = 6
local FRAMES_COOLDOWN_POST_AVANCE = 20
local FRAMES_ESPERA_POR_INTENTO = 40
local REINTENTOS_MAXIMOS = 25
local MAX_PANTALLAS = 500
-- FIX (2026-08-01, drift residual en TEXTO): libro_visto_esta_pantalla se
-- pone en true la PRIMERA vez que se ve modo==7 (icono de libro), pero eso
-- no garantiza que ya paso el ultimo dibujo real de kanji -- puede haber
-- dibujos residuales (animacion del icono, transicion) en los frames
-- siguientes que sigan pasando por el hook con modo 1/8/12 y pisen
-- ultimo_kanji_visto antes de que se tome el snapshot. Se agrega un
-- colchon corto de quietud REAL (frames_desde_ultimo_exec, que solo se
-- resetea con dibujos reales) antes de confiar en el snapshot -- no tan
-- largo como FRAMES_SILENCIO_SIN_TEXTO (esa es la red de seguridad para
-- cuando NUNCA se ve el libro), solo lo suficiente para dejar pasar
-- dibujos residuales de la transicion.
local FRAMES_QUIETUD_POST_LISTO = 20

local function leer(addr, size)
    if size == 1 then return emu.read(addr, emu.memType.wsMemory, false) end
    local lo = emu.read(addr, emu.memType.wsMemory, false)
    local hi = emu.read(addr + 1, emu.memType.wsMemory, false)
    return lo + hi * 256
end

local function historia_nombre(idx)
    return "H" .. (idx + 1)
end

-- ─── Carga de capture_config.ini (formato con secciones, estilo AHK) ───
-- Mismo formato/logica que explorador_autoavance_v1.lua (ver comentario
-- extenso alla): [activo]/historia=<seccion>, secciones [HX] con tope=
-- opcional y P<n>=<opcion> (n = orden de la pregunta, no pantalla),
-- comentarios con ";" a la derecha. Retrocompatible con el formato plano
-- viejo (solo P<n>=<opcion> sin secciones).
local function quitar_comentario(linea)
    local pos = linea:find(";")
    if pos then
        linea = linea:sub(1, pos - 1)
    end
    return linea
end

local function trim(s)
    return s:match("^%s*(.-)%s*$")
end

local function cargar_rutas()
    local rutas_legacy = {}
    local n_legacy = 0
    local f = io.open(CONFIG_FILE, "r")
    if not f then
        emu.log("ADVERTENCIA: no se encontro " .. CONFIG_FILE
            .. " -- se usara opcion 1 en TODAS las preguntas por defecto, sin tope.")
        return rutas_legacy, nil
    end

    local historia_activa = nil
    local seccion_actual = nil
    local secciones = {}

    for linea_raw in f:lines() do
        local linea = trim(quitar_comentario(linea_raw))
        if linea ~= "" then
            local nombre_seccion = linea:match("^%[(.-)%]$")
            if nombre_seccion then
                seccion_actual = nombre_seccion
                if seccion_actual ~= "activo" and not secciones[seccion_actual] then
                    secciones[seccion_actual] = {tope = nil, preguntas = {}}
                end
            else
                local clave, valor = linea:match("^([%w_]+)%s*=%s*(.-)%s*$")
                if clave then
                    valor = trim(valor)
                    if seccion_actual == "activo" then
                        if clave == "historia" then
                            historia_activa = valor
                        end
                    elseif seccion_actual then
                        if clave == "tope" then
                            secciones[seccion_actual].tope = tonumber(valor)
                        else
                            local num_pregunta = clave:match("^P(%d+)$")
                            if num_pregunta then
                                secciones[seccion_actual].preguntas[tonumber(num_pregunta)] = tonumber(valor)
                            end
                        end
                    else
                        local num_pregunta = clave:match("^P(%d+)$")
                        if num_pregunta then
                            rutas_legacy[tonumber(num_pregunta)] = tonumber(valor)
                            n_legacy = n_legacy + 1
                        end
                    end
                end
            end
        end
    end
    f:close()

    if not historia_activa then
        if n_legacy > 0 then
            emu.log(string.format(
                "capture_config.ini cargado (formato plano, sin secciones): %d preguntas configuradas, sin tope.",
                n_legacy))
        else
            emu.log("ADVERTENCIA: " .. CONFIG_FILE
                .. " no tiene [activo] historia=... ni preguntas en formato plano -- se usara opcion 1 en TODAS las preguntas por defecto, sin tope.")
        end
        return rutas_legacy, nil
    end

    local seccion = secciones[historia_activa]
    if not seccion then
        -- CAMBIO (agosto 2026): antes esto era solo una ADVERTENCIA en el
        -- log y seguia con opcion 1 en TODAS las preguntas -- riesgo real
        -- de capturar una ruta entera mal sin darse cuenta (las
        -- advertencias del log no se revisan hasta que ya se nota un
        -- error). Ahora directamente cancela el script.
        error("La historia activa '" .. historia_activa .. "' (definida en [activo] de "
            .. CONFIG_FILE .. ") no tiene una seccion [" .. historia_activa .. "] en ese "
            .. "archivo -- revisa que el nombre coincida EXACTO (mayusculas incluidas) con "
            .. "alguna seccion existente. Script detenido, no se captura nada con opciones "
            .. "por defecto sin que lo notes.")
    end

    local n_preguntas = 0
    for _ in pairs(seccion.preguntas) do n_preguntas = n_preguntas + 1 end
    emu.log(string.format("capture_config.ini cargado: historia activa '%s', %d preguntas configuradas%s.",
        historia_activa, n_preguntas, seccion.tope and (", tope=" .. seccion.tope) or " (sin tope, usa MAX_PANTALLAS)"))
    return seccion.preguntas, seccion.tope
end

local rutas, TOPE_CONFIGURADO = cargar_rutas()

-- ─── Guardado de saves y capturas ───────────────────────────────────────
local saves_dir = BASE_DIR
local os_execute_funciona = true
local function asegurar_carpeta_saves()
    if not os_execute_funciona then return end
    -- FIX (agosto 2026): la version anterior verificaba de verdad
    -- escribiendo+borrando un archivo de prueba dentro de la subcarpeta,
    -- para no confiar ciegamente en que el mkdir haya funcionado. Pero esa
    -- ronda de I/O (mkdir + abrir + escribir + cerrar + borrar) resulto ser
    -- demasiado lenta cuando la carpeta de Mesen esta dentro de OneDrive
    -- (el hook de sincronizacion agrega latencia a cada operacion de
    -- archivo) -- superaba el limite de 1 segundo por llamada que impone
    -- Mesen para scripts Lua, y la funcion se cortaba a mitad de camino
    -- (ANTES de fijar saves_dir), dejando los .mss en la carpeta base sin
    -- ningun aviso claro en el log. Se simplifica a un solo mkdir (fire
    -- and forget) y se fija saves_dir de forma optimista -- si la carpeta
    -- en realidad no se pudo crear, guardar_save_de_pantalla() ya tiene su
    -- propio pcall + aviso por save individual (mas abajo), asi que el
    -- fallo se reporta igual sin bloquear la inicializacion del script.
    local candidata = BASE_DIR .. SAVES_SUBDIR
    local ok_mkdir = pcall(function()
        os.execute('mkdir "' .. candidata .. '" 2>nul')
    end)
    saves_dir = candidata
    if ok_mkdir then
        emu.log("Carpeta de saves: " .. saves_dir .. " (mkdir intentado, sin verificacion "
            .. "de escritura -- ver aviso individual si algun save falla).")
    else
        emu.log("ADVERTENCIA: el intento de mkdir en " .. candidata
            .. " tiro un error de Lua -- se sigue usando esa ruta igual, revisa el "
            .. "log de cada save por si falla.")
    end
end

local aviso_screenshot_dado = false
local contador_sin_traducir = 0
local aviso_save_dado = false

local function guardar_save_de_pantalla(numero_pantalla, historia_str)
    local nombre = string.format("P%05d_%s.mss", numero_pantalla, historia_str)
    local ok, err = pcall(function()
        local datos = emu.createSavestate()
        if datos and datos ~= "" then
            local f = io.open(saves_dir .. nombre, "wb")
            if f then
                f:write(datos)
                f:close()
            else
                if not aviso_save_dado then
                    aviso_save_dado = true
                    emu.log("ADVERTENCIA: no se pudo abrir " .. saves_dir .. nombre
                        .. " para escribir el save (io.open devolvio nil). Revisa permisos/ruta.")
                end
            end
        else
            if not aviso_save_dado then
                aviso_save_dado = true
                emu.log("ADVERTENCIA: emu.createSavestate() no devolvio datos validos para pantalla "
                    .. numero_pantalla .. ".")
            end
        end
    end)
    if not ok then
        emu.log("ADVERTENCIA: fallo guardando save de pantalla #" .. numero_pantalla .. ": " .. tostring(err))
    end
end

-- CAMBIO respecto a v1: ya no es "evidencia de sin traducir" -- se llama
-- SIEMPRE, para toda pantalla, y el nombre indica el estado real
-- (TRADUCIDO_/SIN_TRADUCIR_) en vez de asumir siempre "sin traducir".
local function guardar_screenshot_pantalla(numero_pantalla, historia_str, kanji, png_bytes, sin_traducir)
    local prefijo = sin_traducir and "SIN_TRADUCIR_" or "TRADUCIDO_"
    if sin_traducir then
        contador_sin_traducir = contador_sin_traducir + 1
    end
    local nombre = string.format("%sP%05d_%s_kanji0x%04X", prefijo, numero_pantalla, historia_str, kanji or 0)
    if not png_bytes or png_bytes == "" then
        if not aviso_screenshot_dado then
            aviso_screenshot_dado = true
            emu.log("ADVERTENCIA: no habia captura pendiente para pantalla " .. numero_pantalla
                .. " (emu.takeScreenshot() puede no funcionar en esta build). Se sigue guardando el savestate.")
        end
        return
    end
    local ok_shot, err_shot = pcall(function()
        local f = io.open(BASE_DIR .. nombre .. ".png", "wb")
        if f then
            f:write(png_bytes)
            f:close()
        end
    end)
    if not ok_shot and not aviso_screenshot_dado then
        aviso_screenshot_dado = true
        emu.log("ADVERTENCIA: no se pudo escribir la captura en disco (" .. tostring(err_shot) .. ").")
    end
end

-- ─── Estado general ─────────────────────────────────────────────────────
local activo = false
local pantalla = 1
local pregunta_num = 0
local pantalla_actual_tipo = "TEXTO"
local ignorar_siguiente_pregunta = false
local historia_actual = nil
local ultimo_kanji_visto = nil
local save_pendiente_pantalla = nil
local screenshot_pendiente = nil
local cf0_pendiente = nil  -- es:[0x0CF0] leido ANTES de presionar avanzar -- ver comentario
                            -- extenso en explorador_autoavance_v1.lua (mismo fix aplicado aca).
local libro_visto_esta_pantalla = false
local primer_kanji_pantalla = nil
local frames_desde_pregunta_detectada = 0
-- FIX (2026-08-01, pantallas PREGUNTA): snapshot del kanji tomado en el
-- instante en que se detecta la transicion a PREGUNTA (ver on_exec), ANTES
-- de que el parpadeo del cursor de las opciones tenga chance de disparar
-- el hook de nuevo. A diferencia de TEXTO, en PREGUNTA no se puede esperar
-- "silencio" del hook para confirmar que el kanji esta quieto (el cursor
-- parpadeante lo dispara todo el tiempo mientras se muestran las opciones)
-- -- FRAMES_LISTO_PREGUNTA es un tiempo fijo adivinado, y kanji_antes_de_
-- avanzar (tomado despues de ese tiempo) puede terminar leyendo un kanji
-- de las opciones del menu en vez del ultimo kanji real del dialogo.
local kanji_al_detectar_pregunta = nil
local historia_al_detectar_pregunta = nil

-- NUEVO (2026-08-02): historial de los ultimos N kanjis reales (con
-- AX==0x00FE) vistos en la pantalla actual -- no solo el ultimo. Caso real
-- que motivo esto (H4;152D): el "ultimo" kanji capturado no siempre es el
-- que hace falta para el match del cave -- puede haber mas de un caracter
-- real (puntuacion, espacio, etc.) dibujado despues del que realmente
-- importa, y no hay forma de distinguirlos automaticamente sin conocer la
-- tabla de glifos del juego. Con el historial, si el valor mas reciente no
-- funciona, alcanza con probar el anterior, y el anterior a ese, sin volver
-- a Mesen/Watch Window cada vez.
local HISTORIAL_KANJI_MAX = 5
local historial_kanji = {}  -- lista, mas reciente al final
local historial_kanji_snapshot = nil  -- copia congelada al cerrar la pantalla

local function copiar_lista(t)
    local copia = {}
    for i, v in ipairs(t) do copia[i] = v end
    return copia
end

local fase = "ESPERANDO_TEXTO"
local frames_en_fase = 0
local frames_desde_ultimo_exec = 0
local kanji_antes_de_avanzar = nil
local historia_antes_de_avanzar = nil
local contador_reintentos = 0
-- Cantidad de veces que falta presionar ARRIBA antes de pasar a
-- PRESIONAR_AVANCE (opcion 2 = 1 vez, opcion 3 = 2 veces -- confirmado en
-- vivo por el usuario, agosto 2026). 0 = no hace falta presionar ARRIBA.
local presiones_arriba_pendientes = 0

local eventos = {}
local contador_preguntas_detectadas = 0
local mapeo_preguntas = {}

local function guardar_mapeo()
    local f = io.open(MAPEO_FILE, "w")
    if not f then
        emu.log("ERROR abriendo " .. MAPEO_FILE)
        return
    end
    f:write("-- Mapeo pregunta -> pantalla real -> opcion elegida --\n")
    for _, m in ipairs(mapeo_preguntas) do
        f:write(string.format("Pregunta #%d = Pantalla %d -> opcion %d\n", m.pregunta, m.pantalla, m.opcion))
    end
    f:close()
end

local function on_exec()
    if save_pendiente_pantalla then
        local hist_str_actual = historia_nombre(leer(0x09D8, 1))
        guardar_save_de_pantalla(save_pendiente_pantalla, hist_str_actual)
        save_pendiente_pantalla = nil
    end

    local historia_idx = leer(0x09D8, 1)
    local kanji = leer(0x09DC, 2)
    local modo = leer(0x09DE, 1)

    if modo == 7 then
        libro_visto_esta_pantalla = true
    end

    if modo ~= 1 and modo ~= 8 and modo ~= 12 then return end

    local hist_str = historia_nombre(historia_idx)
    historia_actual = hist_str

    -- FIX RAIZ (2026-08-01): replicar el gate exacto del cave (cmp ax,
    -- 0x00FE) antes de confiar en es:[0x09DC] como "el kanji real".
    -- 0x40D84 (donde esta enganchado este hook) es la MISMA direccion
    -- donde el generador instala el CALL hacia el cave (ver
    -- generar_horizontal_compresion_v19e.py, "rom[base+0]=0xE8" en
    -- 0x340D84/0x740D84) -- es una rutina de despacho de banco
    -- COMPARTIDA, se llama por muchos motivos ademas de dibujar kanji. El
    -- cave mismo (cave_start) solo actua y lee es:[0x09DC] cuando AX ==
    -- 0x00FE en ese instante especifico (cmp ax, 0x00FE / je .es_kanji).
    -- Confirmado en vivo con Watch Window: sin este filtro, este script
    -- capturaba TODAS las llamadas a esa rutina compartida por igual,
    -- pisando ultimo_kanji_visto con lecturas de otras llamadas sin
    -- relacion con el kanji actual (ej. 0x0A36/0x0A38 despues del kanji
    -- real 0x0A30).
    --
    -- IMPORTANTE (correccion sobre el primer intento de este mismo fix):
    -- el gate de AX solo debe aplicar a la CAPTURA del kanji -- NO a la
    -- deteccion de modo/PREGUNTA de mas abajo. Durante una pantalla de
    -- PREGUNTA, el juego puede no volver a llamar a esta rutina con
    -- AX==0x00FE (las opciones ya se dibujaron con kanji real ANTES de
    -- que modo pasara a 12) -- si el gate tambien bloqueaba la deteccion
    -- de "modo==12 -> es una pregunta", esta nunca se detectaba, lo cual
    -- corria la numeracion de pantalla en 1 para todo lo que viniera
    -- despues de la primera pregunta mal detectada (confirmado revisando
    -- las 108 pantallas completas de H6, no solo las que fallaban antes).
    local ok_st, st = pcall(emu.getState)
    local es_kanji_real = ok_st and st and st["cpu.ax"] == 0x00FE
    if es_kanji_real then
        frames_desde_ultimo_exec = 0
        ultimo_kanji_visto = kanji
        if primer_kanji_pantalla == nil then
            primer_kanji_pantalla = kanji
        end
        table.insert(historial_kanji, kanji)
        if #historial_kanji > HISTORIAL_KANJI_MAX then
            table.remove(historial_kanji, 1)
        end
    end

    local modo_efectivo = modo
    if modo == 12 and ignorar_siguiente_pregunta then
        modo_efectivo = 8
    end

    if modo_efectivo == 12 and pantalla_actual_tipo ~= "PREGUNTA" then
        pantalla_actual_tipo = "PREGUNTA"
        ignorar_siguiente_pregunta = true
        frames_desde_pregunta_detectada = 0
        -- ultimo_kanji_visto tiene el ultimo kanji real capturado hasta
        -- ahora (de la ultima llamada con AX==0x00FE, sea esta misma u
        -- otra anterior) -- el menu de opciones todavia no empezo a
        -- parpadear.
        kanji_al_detectar_pregunta = ultimo_kanji_visto
        historia_al_detectar_pregunta = hist_str
        historial_kanji_snapshot = copiar_lista(historial_kanji)
    end
end

emu.addMemoryCallback(on_exec, emu.callbackType.exec, 0x40D84, 0x40D84, emu.cpuType.ws)

local function on_input()
    if not activo then return end
    local input = emu.getInput(0)
    if fase == "PRESIONAR_ARRIBA" then
        input[BOTON_ARRIBA] = true
    elseif fase == "PRESIONAR_AVANCE" then
        input[BOTON_AVANCE] = true
    end
    emu.setInput(input)
end

emu.addEventCallback(on_input, emu.eventType.inputPolled)

-- ─── Logica de avance (corre una vez por frame) ────────────────────────
local function cerrar_pantalla_y_avanzar()
    -- FIX (mismo que en v1): usar cf0_pendiente (leido ANTES de presionar
    -- el boton) en vez de releer es:[0x0CF0] aca -- para este momento la
    -- pantalla SIGUIENTE ya confirmo su propio kanji nuevo, y si el cave
    -- resetea es:[0x0CF0]=0 al arrancar el bloque nuevo, releerlo aca
    -- devolvia el valor de la pantalla NUEVA, no el de la que se cierra --
    -- causaba que pantallas realmente traducidas se guardaran con el
    -- prefijo SIN_TRADUCIR_ por error.
    local cf0 = cf0_pendiente or 0
    local sin_traducir = (cf0 ~= 1)

    -- FIX (2026-08-01): NO usar ultimo_kanji_visto/historia_actual aca --
    -- son globales que on_exec() sigue actualizando en vivo, y la condicion
    -- que dispara este cierre (ultimo_kanji_visto ~= kanji_antes_de_avanzar,
    -- ver CONFIRMANDO_AVANCE) se cumple JUSTO cuando la pantalla SIGUIENTE
    -- ya dibujo su primer kanji. O sea, para cuando llegamos aca,
    -- ultimo_kanji_visto ya NO es el ultimo kanji de la pantalla que se
    -- cierra -- es el primer kanji (o uno de los primeros) de la pantalla
    -- nueva. Esto causaba un drift sistematico chico en texto normal (el
    -- kanji real de la pantalla siguiente arranca unos bytes despues en la
    -- ROM) y saltos grandes en pantallas justo despues de un PREGUNTA (la
    -- pantalla siguiente puede estar en un banco totalmente distinto segun
    -- la rama elegida). El snapshot correcto, tomado ANTES de presionar el
    -- boton de avance (con la pantalla vieja todavia en pantalla, quieta),
    -- es kanji_antes_de_avanzar/historia_antes_de_avanzar.
    --
    -- EXCEPCION (2026-08-01): en pantallas de tipo PREGUNTA, incluso
    -- kanji_antes_de_avanzar puede estar contaminado -- el cursor
    -- parpadeante del menu de opciones sigue disparando el hook mientras
    -- se esperan los FRAMES_LISTO_PREGUNTA fijos, asi que para cuando se
    -- toma ese snapshot ya pueden haberse colado kanjis de las opciones
    -- del menu en vez del ultimo kanji real del dialogo. Para PREGUNTA se
    -- usa en cambio kanji_al_detectar_pregunta/historia_al_detectar_
    -- pregunta, tomado en el instante mismo de la transicion a PREGUNTA
    -- (ver on_exec), antes de que el menu de opciones tenga chance de
    -- parpadear.
    local es_pregunta = (pantalla_actual_tipo == "PREGUNTA")
    local ultimo_kanji_final = (es_pregunta and kanji_al_detectar_pregunta)
        or kanji_antes_de_avanzar or ultimo_kanji_visto
    local historia_final = (es_pregunta and historia_al_detectar_pregunta)
        or historia_antes_de_avanzar or historia_actual

    table.insert(eventos, {
        pantalla = pantalla,
        tipo = pantalla_actual_tipo,
        sin_traducir = sin_traducir,
        historia = historia_final,
        primer_kanji = primer_kanji_pantalla,
        ultimo_kanji = ultimo_kanji_final,
        historial_kanji = historial_kanji_snapshot or {},
    })
    emu.log(string.format("Pantalla %d cerrada (%s%s) [0x0CF0=%d]", pantalla, pantalla_actual_tipo,
        sin_traducir and ", SIN TRADUCIR" or "", cf0))

    -- CAMBIO respecto a v1: se guarda SIEMPRE, no solo si sin_traducir --
    -- esta es la diferencia central de esta variante (ver cabecera).
    guardar_screenshot_pantalla(pantalla, historia_final, ultimo_kanji_final, screenshot_pendiente, sin_traducir)
    screenshot_pendiente = nil
    cf0_pendiente = nil

    pantalla = pantalla + 1
    pantalla_actual_tipo = "TEXTO"
    ignorar_siguiente_pregunta = false
    libro_visto_esta_pantalla = false
    primer_kanji_pantalla = nil
    frames_desde_pregunta_detectada = 0
    kanji_al_detectar_pregunta = nil
    historia_al_detectar_pregunta = nil
    historial_kanji = {}
    historial_kanji_snapshot = nil
    save_pendiente_pantalla = pantalla

    if pantalla > MAX_PANTALLAS then
        activo = false
        emu.log(">>> LIMITE MAX_PANTALLAS alcanzado, avance automatico detenido.")
    end
end

local function on_end_frame()
    if not activo then return end

    frames_desde_ultimo_exec = frames_desde_ultimo_exec + 1
    frames_en_fase = frames_en_fase + 1
    if pantalla_actual_tipo == "PREGUNTA" then
        frames_desde_pregunta_detectada = frames_desde_pregunta_detectada + 1
    end

    if fase == "ESPERANDO_TEXTO" then
        local listo = libro_visto_esta_pantalla
            or (pantalla_actual_tipo == "PREGUNTA" and frames_desde_pregunta_detectada >= FRAMES_LISTO_PREGUNTA)
            or (frames_desde_ultimo_exec >= FRAMES_SILENCIO_SIN_TEXTO)
        if listo then
            if pantalla_actual_tipo == "PREGUNTA" then
                pregunta_num = pregunta_num + 1
                contador_preguntas_detectadas = contador_preguntas_detectadas + 1
                local opcion = rutas[pregunta_num]
                if not opcion then
                    opcion = 1
                    emu.log(string.format(
                        "AVISO: pregunta #%d sin entrada en capture_config.ini -- usando opcion 1 por defecto.",
                        pregunta_num))
                end
                emu.log(string.format("Pregunta #%d detectada (pantalla %d) -> opcion %d", pregunta_num, pantalla, opcion))
                table.insert(mapeo_preguntas, {pregunta = pregunta_num, pantalla = pantalla, opcion = opcion})
                guardar_mapeo()
                if opcion == 2 then
                    presiones_arriba_pendientes = 1
                    fase = "PRESIONAR_ARRIBA"
                elseif opcion == 3 then
                    presiones_arriba_pendientes = 2
                    fase = "PRESIONAR_ARRIBA"
                else
                    presiones_arriba_pendientes = 0
                    fase = "PRESIONAR_AVANCE"
                end
            else
                -- NUEVO: para TEXTO, no pasar directo a presionar el boton --
                -- primero confirmar quietud real (ver FRAMES_QUIETUD_POST_LISTO).
                -- Las PREGUNTA siguen igual que antes (su propio snapshot ya
                -- se toma aparte, en el instante de la transicion -- ver
                -- kanji_al_detectar_pregunta).
                fase = "CONFIRMANDO_QUIETUD"
            end
            contador_reintentos = 0
            frames_en_fase = 0
        end

    elseif fase == "CONFIRMANDO_QUIETUD" then
        if frames_desde_ultimo_exec >= FRAMES_QUIETUD_POST_LISTO then
            fase = "PRESIONAR_AVANCE"
            frames_en_fase = 0
        end

    elseif fase == "PRESIONAR_ARRIBA" then
        if frames_en_fase >= FRAMES_PRESION then
            fase = "PAUSA_ENTRE_BOTONES"
            frames_en_fase = 0
        end

    elseif fase == "PAUSA_ENTRE_BOTONES" then
        if frames_en_fase >= FRAMES_PAUSA_ENTRE_BOTONES then
            presiones_arriba_pendientes = presiones_arriba_pendientes - 1
            if presiones_arriba_pendientes > 0 then
                -- Opcion 3 (u otra que requiera mas de una presion de ARRIBA
                -- en el futuro): volver a presionar antes de avanzar.
                fase = "PRESIONAR_ARRIBA"
            else
                fase = "PRESIONAR_AVANCE"
            end
            frames_en_fase = 0
        end

    elseif fase == "PRESIONAR_AVANCE" then
        if frames_en_fase == 1 then
            kanji_antes_de_avanzar = ultimo_kanji_visto
            historia_antes_de_avanzar = historia_actual
            -- Solo pisar el snapshot de historial si esta pantalla NO es una
            -- PREGUNTA -- para PREGUNTA ya se tomo en on_exec, en el instante
            -- de la transicion (mas confiable, ver comentario alla).
            if pantalla_actual_tipo ~= "PREGUNTA" then
                historial_kanji_snapshot = copiar_lista(historial_kanji)
            end

            if contador_reintentos == 0 then
                cf0_pendiente = leer(0x0CF0, 2)
                local ok_shot, resultado = pcall(emu.takeScreenshot)
                if ok_shot then
                    screenshot_pendiente = resultado
                else
                    screenshot_pendiente = nil
                end
            end
        end
        if frames_en_fase >= FRAMES_PRESION then
            fase = "CONFIRMANDO_AVANCE"
            frames_en_fase = 0
        end

    elseif fase == "CONFIRMANDO_AVANCE" then
        local hay_kanji_nuevo = (ultimo_kanji_visto ~= kanji_antes_de_avanzar)
            or (historia_actual ~= historia_antes_de_avanzar)

        if hay_kanji_nuevo then
            contador_reintentos = 0
            cerrar_pantalla_y_avanzar()
            fase = "COOLDOWN"
            frames_en_fase = 0
        elseif frames_en_fase >= FRAMES_ESPERA_POR_INTENTO then
            contador_reintentos = contador_reintentos + 1
            if contador_reintentos >= REINTENTOS_MAXIMOS then
                -- FIX (2026-08-28, idea del usuario): se agotaron los reintentos sin
                -- detectar kanji nuevo. Esto pasa de forma sistematica en la ULTIMA
                -- pantalla de una historia, justo antes de los creditos ("第N譚・終") --
                -- la transicion a creditos no dispara el hook de captura de kanji, asi
                -- que "hay_kanji_nuevo" nunca se cumple y antes esta pantalla se perdia
                -- sin guardarse (ni traducida ni SIN_TRADUCIR). Ahora, en vez de
                -- descartarla en silencio, se la trata igual que un avance real: se
                -- guarda con cerrar_pantalla_y_avanzar() (usa el screenshot_pendiente/
                -- cf0_pendiente ya capturados en el primer intento) y se detiene el
                -- avance automatico -- no tiene sentido seguir esperando mas pantallas
                -- despues de esto, sea porque termino la historia o porque el input
                -- realmente dejo de llegar (caso raro, distinguible en el log/captura).
                emu.log(string.format(
                    ">>> Se agotaron %d reintentos sin detectar avance real (kanji antes=0x%04X, sigue "
                    .. "igual). Probablemente es el cierre de la historia (transicion a creditos, que no "
                    .. "dispara el hook de kanji). Se guarda esta pantalla como cierre y se detiene el "
                    .. "avance automatico -- revisar la captura si en realidad la historia seguia.",
                    REINTENTOS_MAXIMOS, kanji_antes_de_avanzar or 0))
                contador_reintentos = 0
                cerrar_pantalla_y_avanzar()
                activo = false
            else
                emu.log(string.format(
                    "AVISO: pantalla %d no avanzo tras presionar el boton (intento %d/%d) -- "
                    .. "reintentando (puede ser una animacion que ignora input un instante).",
                    pantalla, contador_reintentos, REINTENTOS_MAXIMOS))
                fase = "PRESIONAR_AVANCE"
                frames_en_fase = 0
            end
        end

    elseif fase == "COOLDOWN" then
        if frames_en_fase >= FRAMES_COOLDOWN_POST_AVANCE then
            fase = "ESPERANDO_TEXTO"
            frames_en_fase = 0
            frames_desde_ultimo_exec = 0
        end
    end
end

local function volcar()
    local nombre = "explorador_autoavance_captura_total_log_" .. os.time() .. ".csv"
    local f = io.open(BASE_DIR .. nombre, "w")
    if not f then emu.log("ERROR abriendo " .. nombre); return end
    f:write("historia;pantalla;tipo;primer_kanji;ultimo_kanji;sin_traducir\n")
    for _, ev in ipairs(eventos) do
        f:write(string.format("%s;%d;%s;0x%04X;0x%04X;%s\n",
            ev.historia or "", ev.pantalla, ev.tipo,
            ev.primer_kanji or 0, ev.ultimo_kanji or 0,
            ev.sin_traducir and "SI" or "no"))
    end
    f:close()
    emu.log("Log volcado en: " .. BASE_DIR .. nombre)
    emu.log(string.format("Preguntas respondidas: %d", contador_preguntas_detectadas))
    emu.log(string.format("Pantallas sin traducir: %d", contador_sin_traducir))

    -- NUEVO (2026-08-02): archivo APARTE (no toca el formato del log de
    -- siempre, a proposito -- ver METODOLOGIA_PROYECTO.md) con los ultimos
    -- HISTORIAL_KANJI_MAX kanjis reales de cada pantalla, mas reciente
    -- primero. Sirve para cuando el "ultimo_kanji" del log de siempre no
    -- dispara el cave -- en vez de volver a Mesen con Watch Window/
    -- breakpoints, se prueban directo los candidatos de esta lista.
    local nombre_hist = "explorador_autoavance_historial_kanji_" .. os.time() .. ".csv"
    local fh = io.open(BASE_DIR .. nombre_hist, "w")
    if not fh then
        emu.log("ERROR abriendo " .. nombre_hist)
        return
    end
    fh:write("historia;pantalla;candidatos_mas_reciente_primero\n")
    for _, ev in ipairs(eventos) do
        local hist_kanji = ev.historial_kanji or {}
        local partes = {}
        for i = #hist_kanji, 1, -1 do
            table.insert(partes, string.format("0x%04X", hist_kanji[i]))
        end
        fh:write(string.format("%s;%d;%s\n", ev.historia or "", ev.pantalla, table.concat(partes, ",")))
    end
    fh:close()
    emu.log("Historial de candidatos volcado en: " .. BASE_DIR .. nombre_hist)
end

local f2_estaba, f8_estaba = false, false
local function check_hotkeys()
    local f2 = emu.isKeyPressed("F2")
    local f8 = emu.isKeyPressed("F8")
    if f2 and not f2_estaba and not activo then
        activo = true
        fase = "ESPERANDO_TEXTO"
        frames_en_fase = 0
        frames_desde_ultimo_exec = 0
        emu.log(">>> Avance automatico INICIADO (F2). Pantalla actual: " .. pantalla)
    end
    if f8 and not f8_estaba then
        activo = false
        emu.log(">>> Avance automatico PAUSADO (F8).")
        volcar()
    end
    f2_estaba, f8_estaba = f2, f8
end

emu.addEventCallback(check_hotkeys, emu.eventType.endFrame)
emu.addEventCallback(on_end_frame, emu.eventType.endFrame)

asegurar_carpeta_saves()
save_pendiente_pantalla = pantalla
emu.log("=== EXPLORADOR AUTOAVANCE v1 - CAPTURA TOTAL (auditoria segunda vuelta) ===")
emu.log("Arranca en PAUSA. F2 = iniciar/reanudar avance automatico. F8 = pausar + volcar log.")
emu.log("Config de rutas: " .. CONFIG_FILE .. " (formato P1=1, P2=2, ...)")
emu.log("Mapeo pregunta->pantalla->opcion se va a escribir en: " .. MAPEO_FILE)
emu.log("OJO: guarda una captura de CADA pantalla (traducida o no), no solo las sin traducir.")
