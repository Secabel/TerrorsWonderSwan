import React, { useState, useRef, useMemo } from 'react';
import { ScreenData } from './types';
import { parseCSV, formatCSV, computeLayout, formatearTextoPregunta, DEFAULT_PREGUNTA_LAYOUT, getPreguntaLayout } from './algo';
import { GridCanvas } from './components/GridCanvas';
import { UploadCloud, Download, AlertTriangle, FileText } from 'lucide-react';

export default function App() {
  const [screens, setScreens] = useState<ScreenData[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [historiaFiltro, setHistoriaFiltro] = useState<string>('todas');
  const [tipoFiltro, setTipoFiltro] = useState<string>('todos');
  const [rutaFiltro, setRutaFiltro] = useState<string>('todos');

  const [geminiKey, setGeminiKey] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [genError, setGenError] = useState<string | null>(null);

  const handleSelectIndex = (idx: number | null) => {
    setSelectedIndex(idx);
    setSuggestions([]);
    setGenError(null);
  };

  const historiasDisponibles = useMemo(() => {
    const set = new Set(screens.map(s => s.historia).filter(Boolean));
    return Array.from(set).sort();
  }, [screens]);

  const tiposDisponibles = useMemo(() => {
    const set = new Set(screens.map(s => s.tipo || 'normal').filter(Boolean));
    return Array.from(set).sort();
  }, [screens]);

  const rutasDisponibles = useMemo(() => {
    if (historiaFiltro === 'todas') return [];
    
    const set = new Set<string>();
    screens.forEach(s => {
      if (s.historia === historiaFiltro) {
        const match = s.id.match(/[a-zA-Z]+$/);
        if (match) {
          set.add(match[0].toUpperCase());
        }
      }
    });
    return Array.from(set).sort();
  }, [screens, historiaFiltro]);

  const screensFiltradas = useMemo(() => {
    return screens
      .map((s, idx) => ({ screen: s, idx }))
      .filter(({ screen }) => {
        const matchHistoria = historiaFiltro === 'todas' || screen.historia === historiaFiltro;
        const matchTipo = tipoFiltro === 'todos' || (screen.tipo || 'normal') === tipoFiltro;
        
        let matchRuta = true;
        if (rutaFiltro !== 'todos') {
          const m = screen.id.match(/[a-zA-Z]+$/);
          if (rutaFiltro === 'principal') {
            matchRuta = m === null;
          } else {
            const screenRuta = m ? m[0].toUpperCase() : null;
            matchRuta = screenRuta === rutaFiltro;
          }
        }

        return matchHistoria && matchTipo && matchRuta;
      });
  }, [screens, historiaFiltro, tipoFiltro, rutaFiltro]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMsg(null);
    const reader = new FileReader();
    reader.onload = (evt) => {
      const content = evt.target?.result as string;
      const result = parseCSV(content);
      if (result.error) {
        setErrorMsg(result.error);
      } else {
        setScreens(result.screens);
        handleSelectIndex(result.screens.length > 0 ? 0 : null);
      }
    };
    reader.readAsText(file);
    // Reset input
    if (fileInputRef.current) {
        fileInputRef.current.value = '';
    }
  };

  const handleExport = () => {
    if (screens.length === 0) return;
    const csvStr = formatCSV(screens);
    const blob = new Blob([csvStr], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'translation.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const updateSelectedScreen = (updates: Partial<ScreenData>) => {
    if (selectedIndex === null) return;
    const newScreens = [...screens];
    newScreens[selectedIndex] = { ...newScreens[selectedIndex], ...updates };
    setScreens(newScreens);
  };

  const selectedScreen = selectedIndex !== null ? screens[selectedIndex] : null;

  // Real-time calculation for the visualizer
  const layoutResult = useMemo(() => {
    if (!selectedScreen) return null;
    let textoToRender = selectedScreen.texto;
    if (selectedScreen.tipo === 'pregunta') {
      const pLayout = getPreguntaLayout(selectedScreen);
      const isValid = (pLayout.anchoIzq + pLayout.espacioIzqCentro + pLayout.anchoCentro + pLayout.espacioCentroDer + pLayout.anchoDer + pLayout.espFinal) === selectedScreen.maxChars;
      textoToRender = isValid ? formatearTextoPregunta(
        selectedScreen.opcion2 || '',
        selectedScreen.opcion1 || '',
        selectedScreen.opcion3 || '',
        pLayout.anchoIzq,
        pLayout.anchoCentro,
        pLayout.anchoDer,
        pLayout.espacioIzqCentro,
        pLayout.espacioCentroDer,
        pLayout.espFinal,
        '@'
      ) : selectedScreen.texto;
    }
    return computeLayout(
      textoToRender, 
      selectedScreen.tyOffset, 
      selectedScreen.maxChars
    );
  }, [selectedScreen]);

  const screensWithErrors = useMemo(() => {
    return screens.map((screen, idx) => {
      let textoToRender = screen.texto;
      if (screen.tipo === 'pregunta') {
        const pLayout = getPreguntaLayout(screen);
        const isValid = (pLayout.anchoIzq + pLayout.espacioIzqCentro + pLayout.anchoCentro + pLayout.espacioCentroDer + pLayout.anchoDer + pLayout.espFinal) === screen.maxChars;
        textoToRender = isValid ? formatearTextoPregunta(
          screen.opcion2 || '',
          screen.opcion1 || '',
          screen.opcion3 || '',
          pLayout.anchoIzq,
          pLayout.anchoCentro,
          pLayout.anchoDer,
          pLayout.espacioIzqCentro,
          pLayout.espacioCentroDer,
          pLayout.espFinal,
          '@'
        ) : screen.texto;
      }
      const layout = computeLayout(textoToRender, screen.tyOffset, screen.maxChars);
      return {
        idx,
        screen,
        isCut: layout.horizontalCut || layout.verticalCut || layout.invalidChars.length > 0
      };
    }).filter(s => s.isCut);
  }, [screens]);

  const handleGenerateSuggestions = async () => {
    if (!selectedScreen) return;
    setIsGenerating(true);
    setGenError(null);
    setSuggestions([]);

    const prevScreenTexto = selectedIndex !== null && selectedIndex > 0 ? screens[selectedIndex - 1].texto : "";
    const nextScreenTexto = selectedIndex !== null && selectedIndex < screens.length - 1 ? screens[selectedIndex + 1].texto : "";

    const maxHeight = 16 - selectedScreen.tyOffset;
    const maxCap = 16 * Math.min(selectedScreen.maxChars, maxHeight);

    const promptContext = `
Eres un asistente experto en traducción ajustada a restricciones de espacio (ROM hacking).
Estamos traduciendo un juego y el texto actual excede el espacio visual disponible en pantalla, generando cortes.

TEXTO ACTUAL (Se excede del límite):
"${selectedScreen.texto}"

CONTEXTO NARRATIVO:
Pantalla anterior: "${prevScreenTexto}"
Pantalla siguiente: "${nextScreenTexto}"

RESTRICCIONES DE ESPACIO (¡MUY IMPORTANTE!):
- El texto es procesado por un algoritmo de word-wrap en columnas de hasta ${selectedScreen.maxChars} caracteres de alto.
- El alto máximo real antes de cortarse verticalmente es de ${maxHeight} caracteres.
- Se disponen de un total de 16 columnas en pantalla.
- La capacidad aproximada contando espacios es de unos ~${maxCap} caracteres.
- OBJETIVO: Acorta el texto ORIGINAL lo MÍNIMO NECESARIO para que no exceda las 16 columnas ni se corte. NO hagas un resumen extremo de 80 caracteres si caben 200. Reemplaza palabras por sinónimos más cortos, recorta redundancias sutiles, pero MANTÉN todo el nivel de detalle, estilo y longitud posible del texto original.
- NO PUEDES usar minúsculas, tildes (áéíóú) ni la ñ.
- SOLO USA este conjunto: A-Z, 0-9, y símbolos . , ? ! - : @ espacio.

INSTRUCCIONES:
Proporciona 3 alternativas diferentes reescribiendo el TEXTO ACTUAL para que quepa justo en el espacio, pero siendo lo más largo y detallado que el límite te permita. 
Devuelve el resultado como un objeto JSON estricto con una lista bajo la clave "alternativas".
Formato de salida esperado:
{
  "alternativas": [
    "TEXTO 1 AJUSTADO QUE APROVECHA AL MAXIMO EL ESPACIO...",
    "TEXTO 2...",
    "TEXTO 3..."
  ]
}
`;

    try {
      const payload = {
        contents: [{ parts: [{ text: promptContext }] }],
        generationConfig: {
          responseMimeType: "application/json"
        }
      };

      let data: any = null;
      
      if (geminiKey) {
        // Llamada directa al API de Gemini desde el cliente
        const directResponse = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${geminiKey}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        
        if (!directResponse.ok) {
           const err = await directResponse.json().catch(() => ({}));
           throw new Error(err.error?.message || err.error || "Error al llamar a la API directamente.");
        }
        data = await directResponse.json();
      } else {
        // Llamada a través del backend (proxy)
        const response = await fetch('/api/gemini', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payload }) // Backend injected key
        });
  
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
           const text = await response.text();
           if (text.startsWith('<!')) {
             throw new Error("El backend no está disponible (probablemente estás en un hosting estático como Vercel). Por favor, ingresa tu API Key manualmente en el panel izquierdo.");
           }
           throw new Error("Respuesta no válida del servidor.");
        }
  
        if (!response.ok) {
           const err = await response.json().catch(() => ({}));
           throw new Error(err.error?.message || err.error || "Error al llamar a la API.");
        }
  
        data = await response.json();
      }

      const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
      if (text) {
        const parsed = JSON.parse(text);
        if (parsed.alternativas && Array.isArray(parsed.alternativas)) {
           setSuggestions(parsed.alternativas);
        } else {
           throw new Error("Formato JSON de respuesta inválido.");
        }
      } else {
         throw new Error("Respuesta vacía de la IA.");
      }
    } catch (e: any) {
      setGenError("Error: " + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-theme-bg text-theme-text font-mono flex flex-col overflow-hidden text-[11px]">
      {/* Header */}
      <div className="h-12 bg-theme-panel border-b border-theme-border flex items-center justify-between px-6 shrink-0">
        <h1 className="text-[14px] tracking-[2px] text-theme-accent font-bold m-0 uppercase flex items-center gap-2">
          TERRORS_WS_PREVIEWER_V1.1.20
        </h1>
        <div className="flex gap-3">
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="bg-[#444] text-white border-none px-4 py-2 text-[11px] font-bold cursor-pointer uppercase flex items-center gap-2"
            >
              Cargar CSV
            </button>
            <input 
              type="file" 
              accept=".csv" 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
            />
            {screens.length > 0 && <button 
              onClick={handleExport} 
              disabled={screensWithErrors.some((s) => s.screen.tipo === 'pregunta' && ((s.screen.anchoIzq || 0) + (s.screen.espacioIzqCentro ?? 0) + (s.screen.anchoCentro || 0) + (s.screen.espacioCentroDer ?? 1) + (s.screen.anchoDer || 0) + (s.screen.espFinal ?? 0) !== s.screen.maxChars))}
              className="bg-theme-accent text-black border-none px-4 py-2 text-[11px] font-bold cursor-pointer uppercase flex items-center gap-2 disabled:bg-theme-bg disabled:text-theme-muted disabled:cursor-not-allowed" 
            >
              Exportar
            </button>}
        </div>
      </div>
    
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-[260px] bg-theme-surface border-r border-theme-border flex flex-col shrink-0">
          <div className="flex-1 overflow-y-auto flex flex-col">
            <div className="p-3 bg-theme-panel text-[10px] text-theme-muted uppercase font-bold shrink-0 flex flex-col gap-2">
              <div className="flex flex-col gap-1 mb-1">
                <label className="text-[10px] text-theme-muted uppercase font-bold">Número de pantallas</label>
                <input 
                  type="text" 
                  readOnly 
                  value={`${screensFiltradas.length} / ${screens.length}`} 
                  className="bg-theme-bg border border-theme-border text-theme-accent font-bold p-1 text-[10px] w-full focus:outline-none text-center"
                />
              </div>
              {historiasDisponibles.length > 0 && (
                <select
                  value={historiaFiltro}
                  onChange={(e) => {
                    setHistoriaFiltro(e.target.value);
                    setRutaFiltro('todos'); // reset ruta on historia change
                  }}
                  className="bg-theme-bg border border-theme-border text-theme-text p-1 text-[10px] w-full focus:outline-none focus:border-theme-accent"
                >
                  <option value="todas">Todas las historias</option>
                  {historiasDisponibles.map(h => (
                    <option key={h} value={h}>Historia {h}</option>
                  ))}
                </select>
              )}
              {tiposDisponibles.length > 0 && (
                <select
                  value={tipoFiltro}
                  onChange={(e) => setTipoFiltro(e.target.value)}
                  className="bg-theme-bg border border-theme-border text-theme-text p-1 text-[10px] w-full focus:outline-none focus:border-theme-accent"
                >
                  <option value="todos">Todos los tipos</option>
                  {tiposDisponibles.map(t => (
                    <option key={t} value={t}>Tipo: {t}</option>
                  ))}
                </select>
              )}
              {historiaFiltro !== 'todas' && rutasDisponibles.length > 0 && (
                <select
                  value={rutaFiltro}
                  onChange={(e) => setRutaFiltro(e.target.value)}
                  className="bg-theme-bg border border-theme-border text-theme-text p-1 text-[10px] w-full focus:outline-none focus:border-theme-accent"
                >
                  <option value="todos">Todos</option>
                  <option value="principal">Principal</option>
                  {rutasDisponibles.map(r => (
                    <option key={r} value={r}>Ruta: {r}</option>
                  ))}
                </select>
              )}
            </div>
            
            {errorMsg ? (
              <div className="mx-3 mt-3 text-xs text-theme-error bg-theme-error/10 p-2 rounded border border-theme-error/30 uppercase">
                Error: {errorMsg}
              </div>
            ) : screens.length === 0 ? (
              <div className="text-center text-theme-muted text-[11px] mt-8 px-4 flex flex-col items-center">
                <FileText className="mb-2 opacity-50" size={24} />
                <p>No hay pantallas cargadas.</p>
              </div>
            ) : screensFiltradas.length === 0 ? (
              <div className="text-center text-theme-muted text-[11px] mt-8 px-4 flex flex-col items-center">
                <p>No hay pantallas para esta historia.</p>
              </div>
            ) : (
              <div className="flex flex-col">
                {screensFiltradas.map(({ screen, idx }) => (
                  <div
                    key={`${screen.historia}-${screen.id}-${idx}`}
                    onClick={() => handleSelectIndex(idx)}
                    className={`px-4 py-3 border-b border-theme-border cursor-pointer flex flex-col gap-1 ${
                      selectedIndex === idx 
                        ? 'bg-[rgba(0,255,136,0.1)] border-l-[4px] border-l-theme-accent' 
                        : 'border-l-[4px] border-l-transparent hover:bg-theme-panel'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-theme-text truncate">{screen.historia} - {screen.id}</div>
                    <div className="text-[10px] text-theme-muted truncate" title={screen.tipo === 'pregunta' ? screen.opcion1 : screen.texto}>
                      {(screen.tipo === 'pregunta' ? screen.opcion1 : screen.texto) || <span className="opacity-40 italic">Vacío</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* API Key Config in Sidebar Bottom */}
          <div className="p-3 border-t border-theme-border bg-theme-panel shrink-0 flex flex-col gap-2">
            <label className="text-[10px] text-theme-muted uppercase font-bold" title="Si lo configuras en .env o Secrets, no necesitas ponerlo aquí.">API Key Gemini (IA) Opcional</label>
            <input 
                type="password" 
                value={geminiKey} 
                onChange={e => setGeminiKey(e.target.value)} 
                placeholder="Detecta Auth Automático..."
                className="bg-theme-bg border border-theme-border text-theme-text p-2 w-full box-border font-inherit text-[11px] focus:outline-none focus:border-theme-accent"
            />
            <p className="text-[9px] text-theme-muted leading-tight">Para hostings estáticos (ej: Vercel).</p>
          </div>
        </div>
    
        {/* Workspace */}
        <div className="flex-1 bg-black flex items-center justify-center relative">
           {!selectedScreen || !layoutResult ? (
              <div className="text-theme-muted text-[11px] uppercase tracking-wider">
                Inicia cargando un CSV y selecciona una fila.
              </div>
           ) : (
              <>
                <div className="absolute top-5 left-5 text-[10px] text-[#444] uppercase tracking-wider font-bold">
                  DISPLAY: WORD WRAP PREVIEW
                </div>
                
                <div className="relative bg-[#111] p-4 border-2 border-[#333] shadow-[0_0_40px_rgba(0,0,0,0.5)]">
                   <div className="absolute top-0 left-4 -translate-y-full pb-1 text-[10px] text-theme-muted uppercase tracking-widest font-bold">
                      ty: 0 (Arriba) &rarr; 15 (Abajo)
                   </div>
                   <div className="absolute left-0 top-4 -translate-x-full pr-2 text-[10px] text-theme-muted uppercase tracking-widest font-bold rotate-180" style={{ writingMode: 'vertical-rl' }}>
                      tx: 15 (Der) &rarr; 0 (Izq)
                   </div>
                   <div className="grid grid-cols-[repeat(16,28px)] grid-rows-[repeat(16,28px)] gap-[1px] bg-theme-border font-mono relative">
                      {Array.from({ length: 16 }).map((_, rowIndex) => {
                         return Array.from({ length: 16 }).map((_, colIndex) => {
                           const tx = 15 - rowIndex;
                           const ty = colIndex;
                           const tile = layoutResult.tiles.find(t => t.tx === tx && t.ty === ty);
                           
                           return (
                                <div 
                                  key={`${tx}-${ty}`} 
                                  className={`w-7 h-7 flex items-center justify-center text-[18px] font-bold ${tile ? 'bg-theme-bg text-theme-accent' : 'bg-theme-bg text-theme-border/10'}`}
                                >
                                   {tile && tile.c !== '  ' && tile.c !== '@' ? tile.c : ''}
                                </div>
                           );
                         });
                      })}
                   </div>
                </div>
              </>
           )}
        </div>
    
        {/* Editor */}
        <div className="w-[320px] bg-theme-surface border-l border-theme-border flex flex-col gap-4 p-5 shrink-0 overflow-y-auto">
          {selectedScreen && layoutResult && (
            <>
                <div className="flex flex-col mb-4">
                  <label className="flex items-center gap-2 cursor-pointer text-[11px] text-theme-text font-bold uppercase">
                    <input 
                      type="checkbox" 
                      checked={selectedScreen.tipo === 'pregunta'}
                      onChange={(e) => {
                        if (e.target.checked) {
                          updateSelectedScreen({ 
                            tipo: 'pregunta',
                            anchoIzq: selectedScreen.anchoIzq ?? DEFAULT_PREGUNTA_LAYOUT.anchoIzq,
                            anchoCentro: selectedScreen.anchoCentro ?? DEFAULT_PREGUNTA_LAYOUT.anchoCentro,
                            anchoDer: selectedScreen.anchoDer ?? DEFAULT_PREGUNTA_LAYOUT.anchoDer,
                            espacioIzqCentro: selectedScreen.espacioIzqCentro ?? DEFAULT_PREGUNTA_LAYOUT.espacioIzqCentro,
                            espacioCentroDer: selectedScreen.espacioCentroDer ?? DEFAULT_PREGUNTA_LAYOUT.espacioCentroDer,
                            espFinal: selectedScreen.espFinal ?? DEFAULT_PREGUNTA_LAYOUT.espFinal,
                          });
                        } else {
                          updateSelectedScreen({ tipo: 'texto' });
                        }
                      }}
                    />
                    Es pregunta (3 opciones)
                  </label>
                </div>

                {selectedScreen.tipo === 'pregunta' ? (() => {
                  const pLayout = getPreguntaLayout(selectedScreen);
                  const currentSum = pLayout.anchoIzq + pLayout.espacioIzqCentro + pLayout.anchoCentro + pLayout.espacioCentroDer + pLayout.anchoDer + pLayout.espFinal;
                  
                  return (
                  <div className="flex flex-col gap-3">
                    <div className="flex justify-between items-center bg-theme-bg p-2 rounded border border-theme-border">
                       <span className="text-[10px] uppercase font-bold text-theme-muted">Sum widths:</span>
                       <span className={`text-[12px] font-mono font-bold ${
                         currentSum === selectedScreen.maxChars 
                          ? 'text-theme-accent' 
                          : 'text-theme-error'
                       }`}>
                         {currentSum} / {selectedScreen.maxChars}
                       </span>
                    </div>

                    <div className="flex flex-col border border-theme-border p-2 gap-2 bg-theme-bg">
                      <label className="block text-[10px] text-theme-accent uppercase font-bold">Opción 2 (Izquierda)</label>
                      <div className="flex gap-2 items-center">
                        <input 
                          type="number"
                          min="0"
                          title="Ancho columna izquierda"
                          value={pLayout.anchoIzq}
                          onChange={(e) => updateSelectedScreen({ anchoIzq: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                        <input 
                          value={selectedScreen.opcion2 || ''}
                          onChange={(e) => updateSelectedScreen({ opcion2: e.target.value.replace(/\r?\n|\r/g, ' ') })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 flex-1 font-inherit text-[12px] focus:outline-none focus:border-theme-accent"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2 items-center px-2">
                        <label className="text-[10px] uppercase text-theme-muted font-bold">Espaciado Izq-Centro:</label>
                        <input 
                          type="number" min="0" value={pLayout.espacioIzqCentro}
                          onChange={(e) => updateSelectedScreen({ espacioIzqCentro: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                    </div>

                    <div className="flex flex-col border border-theme-border p-2 gap-2 bg-theme-bg">
                      <label className="block text-[10px] text-theme-accent uppercase font-bold">Opción 1 (Centro)</label>
                      <div className="flex gap-2 items-center">
                        <input 
                          type="number"
                          min="0"
                          title="Ancho columna centro"
                          value={pLayout.anchoCentro}
                          onChange={(e) => updateSelectedScreen({ anchoCentro: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                        <input 
                          value={selectedScreen.opcion1 || ''}
                          onChange={(e) => updateSelectedScreen({ opcion1: e.target.value.replace(/\r?\n|\r/g, ' ') })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 flex-1 font-inherit text-[12px] focus:outline-none focus:border-theme-accent"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2 items-center px-2">
                        <label className="text-[10px] uppercase text-theme-muted font-bold">Espaciado Centro-Der:</label>
                        <input 
                          type="number" min="0" value={pLayout.espacioCentroDer}
                          onChange={(e) => updateSelectedScreen({ espacioCentroDer: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                    </div>

                    <div className="flex flex-col border border-theme-border p-2 gap-2 bg-theme-bg">
                      <label className="block text-[10px] text-theme-accent uppercase font-bold">Texto Fijo (Derecha)</label>
                      <div className="flex gap-2 items-center">
                        <input 
                          type="number"
                          min="0"
                          title="Ancho columna derecha"
                          value={pLayout.anchoDer}
                          onChange={(e) => updateSelectedScreen({ anchoDer: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                        <input 
                          value={selectedScreen.opcion3 || ''}
                          onChange={(e) => updateSelectedScreen({ opcion3: e.target.value.replace(/\r?\n|\r/g, ' ') })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 flex-1 font-inherit text-[12px] focus:outline-none focus:border-theme-accent"
                        />
                      </div>
                    </div>

                    <div className="flex gap-2 items-center px-2">
                        <label className="text-[10px] uppercase text-theme-muted font-bold">Espaciado Final:</label>
                        <input 
                          type="number" min="0" value={pLayout.espFinal}
                          onChange={(e) => updateSelectedScreen({ espFinal: Number(e.target.value) })}
                          className="bg-theme-surface border border-theme-border text-theme-text p-1 w-12 font-inherit text-[12px] text-center focus:outline-none focus:border-theme-accent"
                        />
                    </div>

                  </div>
                  );
                })() : (
                  <div className="flex flex-col">
                    <label className="block text-[10px] text-theme-muted mb-1 uppercase font-bold">Texto del Diálogo</label>
                    <textarea 
                      value={selectedScreen.texto}
                      onChange={(e) => updateSelectedScreen({ texto: e.target.value.replace(/\r?\n|\r/g, ' ') })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                        }
                      }}
                      className="bg-theme-bg border border-theme-border text-theme-text p-2 w-full box-border font-inherit text-[12px] h-32 resize-none focus:outline-none focus:border-theme-accent"
                      placeholder="ESCRIBE AQUI"
                    />
                  </div>
                )}
    
                <div className="flex gap-3">
                  <div className="flex-1 flex flex-col">
                    <label className="block text-[10px] text-theme-muted mb-1 uppercase font-bold">TY_OFFSET</label>
                    <input 
                      type="number" 
                      min="0"
                      max="15"
                      value={selectedScreen.tyOffset}
                      onChange={(e) => updateSelectedScreen({ tyOffset: parseInt(e.target.value) || 0 })}
                      className="bg-theme-bg border border-theme-border text-theme-text p-2 w-full box-border font-inherit text-[12px] focus:outline-none focus:border-theme-accent"
                    />
                  </div>
                  <div className="flex-1 flex flex-col">
                    <label className="block text-[10px] text-theme-muted mb-1 uppercase font-bold">MAX_CHARS</label>
                    <input 
                      type="number" 
                      min="1"
                      max="16"
                      value={selectedScreen.maxChars}
                      onChange={(e) => updateSelectedScreen({ maxChars: parseInt(e.target.value) || 1 })}
                      className="bg-theme-bg border border-theme-border text-theme-text p-2 w-full box-border font-inherit text-[12px] focus:outline-none focus:border-theme-accent"
                    />
                  </div>
                </div>

                {(layoutResult.horizontalCut || layoutResult.verticalCut || layoutResult.invalidChars.length > 0) && (
                  <div className="mt-2 text-theme-error text-[10px] font-bold uppercase space-y-1 bg-theme-error/10 p-2 border border-theme-error/20 rounded">
                    {layoutResult.invalidChars.length > 0 && <div className="flex items-start gap-1"><AlertTriangle size={12} className="shrink-0"/> CARACTERES INVÁLIDOS: {layoutResult.invalidChars.join(', ')}</div>}
                    {layoutResult.horizontalCut && <div className="flex items-start gap-1 flex-col">
                        <div className="flex items-center gap-1"><AlertTriangle size={12} className="shrink-0"/> ⚠ EL TEXTO SE CORTA EN COLUMNA (HORIZONTAL):</div>
                        <div className="text-theme-error/70 ml-4 font-mono truncate w-full" title={layoutResult.cutHorizontalText.join(' ')}>"{layoutResult.cutHorizontalText.join(' ')}"</div>
                        <div className="text-theme-error/80 ml-4">Columnas utilizadas: {layoutResult.usedCols} / Columnas máximas (por pantalla): {layoutResult.maxCols}</div>
                    </div>}
                    {layoutResult.verticalCut && <div className="flex items-start gap-1 flex-col">
                        <div className="flex items-center gap-1"><AlertTriangle size={12} className="shrink-0"/> ⚠ EL TEXTO SE CORTA AL FINAL (VERTICAL):</div>
                        <div className="text-theme-error/70 ml-4 font-mono truncate w-full" title={layoutResult.cutVerticalText.join(' ')}>"{layoutResult.cutVerticalText.join(' ')}"</div>
                    </div>}
                  </div>
                )}
    
                {(layoutResult.horizontalCut || layoutResult.verticalCut) && (
                  <div className="mt-2 border border-theme-accent/30 bg-theme-accent/5 p-3 flex flex-col gap-3">
                    <div className="text-[11px] text-theme-accent font-bold uppercase">Asistente IA de Ajuste</div>
                    <button
                      onClick={handleGenerateSuggestions}
                      disabled={isGenerating}
                      className={`border border-theme-accent/50 px-4 py-2 text-[11px] font-bold cursor-pointer uppercase flex items-center justify-center gap-2 ${isGenerating ? 'bg-theme-muted/10 text-theme-muted opacity-50' : 'bg-theme-accent/10 text-theme-accent hover:bg-theme-accent/30'}`}
                    >
                      {isGenerating ? "Generando..." : "Sugerir texto alternativo"}
                    </button>
                    {genError && <div className="text-theme-error text-[10px] uppercase font-bold bg-theme-error/10 p-2">{genError}</div>}
                    {suggestions.length > 0 && (
                      <div className="flex flex-col gap-2 mt-2">
                        {suggestions.map((sug, i) => {
                          const lResult = computeLayout(sug, selectedScreen.tyOffset, selectedScreen.maxChars);
                          const isCut = lResult.horizontalCut || lResult.verticalCut;
                          return (
                            <div key={i} className="flex flex-col gap-2 p-2 border border-theme-border bg-theme-bg">
                               <div className="text-[11px] text-theme-text font-mono whitespace-pre-wrap leading-tight">{sug}</div>
                               <div className="flex justify-between items-center border-t border-theme-border/50 pt-2 mt-1">
                                 <div className={`text-[9px] font-bold uppercase ${isCut || lResult.invalidChars.length ? 'text-theme-error' : 'text-theme-accent'}`}>
                                    {isCut ? 'CORTADO' : 'CABE BIEN'} | L: {sug.length}
                                 </div>
                                 <button 
                                   onClick={() => updateSelectedScreen({ texto: sug })}
                                   className="bg-theme-panel border border-theme-border text-theme-text hover:text-theme-accent hover:border-theme-accent/50 px-2 py-1 text-[9px] font-bold cursor-pointer uppercase transition-colors"
                                 >
                                   Usar esta
                                 </button>
                               </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-5 border-t border-theme-border pt-5">
                  <div className="text-[11px] text-theme-muted mb-2 uppercase font-bold text-center">VISTA PREVIA WS_V_ORIENTED:</div>
                  <div className="bg-[#111] p-1 border-2 border-[#333] shadow-inner relative max-w-[240px] mx-auto">
                    <GridCanvas layout={layoutResult} />
                  </div>
                </div>

                {screensWithErrors.length > 0 && (
                  <div className="mt-4 flex flex-col gap-2 bg-theme-panel border border-theme-border p-3">
                    <label className="text-[10px] text-theme-error font-bold uppercase flex items-center gap-1">
                       <AlertTriangle size={12} /> Ir a pantallas con advertencias ({screensWithErrors.length}):
                    </label>
                    <select
                      className="bg-theme-bg border border-theme-border text-theme-text p-2 text-[11px] w-full focus:outline-none focus:border-theme-accent font-mono truncate"
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val !== "") handleSelectIndex(Number(val));
                      }}
                      value={selectedIndex !== null && screensWithErrors.some(s => s.idx === selectedIndex) ? selectedIndex : ""}
                    >
                      <option value="" disabled>Selecciona una pantalla...</option>
                      {screensWithErrors.map((s) => {
                        const previewText = s.screen.tipo === 'pregunta' ? s.screen.opcion1 : s.screen.texto;
                        return (
                          <option key={s.idx} value={s.idx}>
                            [{s.screen.id}] {previewText ? previewText.substring(0, 20) + '...' : 'Vacío'}
                          </option>
                        );
                      })}
                    </select>
                  </div>
                )}
            </>
          )}
        </div>
      </div>
    
      <div className="h-7 bg-theme-accent text-black flex items-center px-3 text-[10px] font-bold shrink-0">
         SYSTEM READY | TX: 15..0 | TY: 0..15 | FONT: 5x5_MONO | MODE: STANDALONE
      </div>
    </div>
  );
}

