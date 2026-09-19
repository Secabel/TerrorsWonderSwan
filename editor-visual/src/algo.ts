import { FONT_JSON } from './font';
import { Tile, LayoutResult } from './types';

/**
 * Exact replica of the Python word_wrap function provided in the spec.
 */
export function wordWrap(texto: string, maxCols: number): string[] {
  if (maxCols <= 0) return [];
  // Use filter(Boolean) to ignore multiple contiguous spaces matching Python's default split()
  const palabras = texto.toUpperCase().split(/\s+/).filter(Boolean);
  const fragmentos: string[] = [];

  for (let p of palabras) {
    while (p.length > maxCols) {
      fragmentos.push(p.substring(0, maxCols));
      p = p.substring(maxCols);
    }
    if (p.length > 0) fragmentos.push(p);
  }

  const cols: string[] = [];
  let currentCol = '';

  for (const p of fragmentos) {
    if (!currentCol) {
      currentCol = p;
    } else if (currentCol.length + 1 + p.length <= maxCols) {
      currentCol += ' ' + p;
    } else {
      cols.push(currentCol);
      currentCol = p;
    }
  }

  if (currentCol) {
    cols.push(currentCol);
  }

  return cols;
}

/**
 * Exact replica of the Python make_tile_tabla logic, 
 * augmented with error detection metadata for the visualizer.
 */
export function computeLayout(texto: string, tyOffset: number, maxChars: number): LayoutResult {
  const cols = wordWrap(texto, maxChars);
  const tiles: Tile[] = [];
  let horizontalCut = false;
  let verticalCut = false;
  const cutHorizontalText: string[] = [];
  const cutVerticalText: string[] = [];
  const invalidChars = new Set<string>();

  for (let colIdx = 0; colIdx < cols.length; colIdx++) {
    const col = cols[colIdx];
    // First visual text column goes strictly to 15 (rightmost). Then moves left (14, 13...).
    const tx = 15 - colIdx;
    
    if (tx < 0) {
      const remainingColsText = cols.slice(colIdx).join(' ').trim();
      if (remainingColsText.length > 0) {
        horizontalCut = true;
        cutHorizontalText.push(remainingColsText);
      }
      break; // Exhausted available columns -> Horizontal Cut (CORTADO)
    }

    for (let tyIdx = 0; tyIdx < col.length; tyIdx++) {
      const c = col[tyIdx];
      const ty = tyIdx + tyOffset;

      // Checking against our defined font
      const keyStr = c === ' ' ? '  ' : c; // Our font JSON uses '  ' for space, but typical text uses ' '
      if (!FONT_JSON[keyStr] && keyStr !== '@') {
        invalidChars.add(c);
      }

      if (ty > 15) {
        const remainingChars = col.substring(tyIdx).trim();
        if (remainingChars.length > 0) {
           verticalCut = true;
           cutVerticalText.push(`"${remainingChars}" ("${col.trim()}")`);
        }
        break; // Exhausted available rows downward -> Vertical Cut (CORTADO)
      }

      tiles.push({ tx, ty, c: keyStr });
    }
  }

  return { 
    tiles, 
    horizontalCut, 
    verticalCut, 
    cutHorizontalText,
    cutVerticalText,
    invalidChars: Array.from(invalidChars),
    usedCols: cols.length,
    maxCols: 16
  };
}

export function obtenerFragmentos(texto: string, ancho: number, caracter: string): string[] {
  const palabras = texto.split(/\s+/).filter(Boolean);
  const fragmentos: string[] = [];
  if (!ancho || ancho < 1) return fragmentos;
  
  for (const palabra of palabras) {
    for (let i = 0; i < palabra.length; i += ancho) {
      let trozo = palabra.substring(i, i + ancho);
      if (trozo.length < ancho) {
        trozo = trozo + caracter.repeat(ancho - trozo.length);
      }
      fragmentos.push(trozo);
    }
  }
  return fragmentos;
}

export function formatearTextoPregunta(
  opcion2: string,
  opcion1: string,
  textoFijo: string,
  anchoIzq: number,
  anchoCentro: number,
  anchoDer: number,
  espacioIzqCentro: number,
  espacioCentroDer: number,
  espFinal: number,
  caracter: string
): string {
  if (!anchoIzq && !anchoCentro && !anchoDer) return "";

  const fragIzq = obtenerFragmentos(opcion2, anchoIzq, caracter);
  const fragCentro = obtenerFragmentos(opcion1, anchoCentro, caracter);
  const fragDer = obtenerFragmentos(textoFijo, anchoDer, caracter);

  const maxLen = Math.max(fragIzq.length, fragCentro.length, fragDer.length);
  const rellenoIzq = caracter.repeat(anchoIzq);
  const rellenoCentro = caracter.repeat(anchoCentro);
  const rellenoDer = caracter.repeat(anchoDer);
  
  const sep1 = caracter.repeat(espacioIzqCentro);
  const sep2 = caracter.repeat(espacioCentroDer);
  const sepFinal = caracter.repeat(espFinal);

  const resultado: string[] = [];
  for (let i = 0; i < maxLen; i++) {
    const izq = i < fragIzq.length ? fragIzq[i] : rellenoIzq;
    const centro = i < fragCentro.length ? fragCentro[i] : rellenoCentro;
    const der = i < fragDer.length ? fragDer[i] : rellenoDer;
    resultado.push(`${izq}${sep1}${centro}${sep2}${der}${sepFinal}`);
  }

  return resultado.join(' ');
}

export function decodificarTextoPregunta(
  texto: string,
  anchoIzq: number,
  espIzqCentro: number,
  anchoCentro: number,
  espCentroDer: number,
  anchoDer: number,
  espFinal: number,
  maxChars: number,
  caracter: string
) {
  const filas: string[] = [];
  let i = 0;
  while (i < texto.length) {
    filas.push(texto.substring(i, i + maxChars));
    i += maxChars + 1;
  }
  
  const fragIzq: string[] = [];
  const fragCentro: string[] = [];
  const fragDer: string[] = [];
  
  for (const fila of filas) {
    // If the fila is shorter than maxChars (e.g. malformed or last one stripped), pad it locally
    const safeFila = fila.padEnd(maxChars, ' ');
    let pos = 0;
    
    fragIzq.push(safeFila.substring(pos, pos + anchoIzq));
    pos += anchoIzq + espIzqCentro;
    
    fragCentro.push(safeFila.substring(pos, pos + anchoCentro));
    pos += anchoCentro + espCentroDer;
    
    fragDer.push(safeFila.substring(pos, pos + anchoDer));
  }

  function reconstruir(fragmentos: string[], ancho: number): string {
    let resultado = "";
    const rellenoVacioAT = caracter.repeat(ancho);
    const rellenoVacioSpace = " ".repeat(ancho);
    
    for (const frag of fragmentos) {
      if (frag === rellenoVacioAT || frag === rellenoVacioSpace) {
         resultado += " ";
      } else {
         const hasAt = frag.includes(caracter);
         let clean = frag.replace(new RegExp(caracter, 'g'), '');
         const hasSpace = clean.endsWith(' ');
         clean = clean.trim();
         
         resultado += clean;
         if (hasAt || hasSpace) {
            resultado += " ";
         }
      }
    }
    return resultado.trim().replace(/\s+/g, ' ');
  }
  
  return {
     opcion2: reconstruir(fragIzq, anchoIzq),
     opcion1: reconstruir(fragCentro, anchoCentro),
     opcion3: reconstruir(fragDer, anchoDer)
  };
}

export function parseCSV(raw: string): { screens: import('./types').ScreenData[], error?: string } {
  try {
    const lines = raw.split(/\r?\n/).filter(line => line.trim() !== '');
    if (lines.length === 0) {
      return { screens: [], error: 'El archivo CSV está vacío.' };
    }

    const headerParts = lines[0].toLowerCase().split(';');
    if (headerParts.length < 5 || headerParts[0].trim() !== 'historia' || headerParts[1].trim() !== 'pantalla') {
      return { screens: [], error: 'Formato de CSV inválido. El archivo debe incluir las columnas "historia;pantalla;texto;ty_offset;max_chars..." en ese orden exacto.' };
    }

    const data: import('./types').ScreenData[] = [];
    
    // Assuming CSV columns: historia;pantalla;texto;ty_offset;max_chars;primer_kanji;ultimo_kanji;tipo;revisado
    for (let i = 0; i < lines.length; i++) {
        const parts = lines[i].split(';');
        if (parts.length >= 5) {
            const tyOffset = parseInt(parts[3].trim(), 10);
            const maxChars = parseInt(parts[4].trim(), 10);

            // Skip headers row
            if (isNaN(tyOffset) || isNaN(maxChars)) {
                continue;
            }

            const rawTexto = parts[2] !== undefined ? parts[2].trim() : '';
            const tipo = parts[7] !== undefined ? parts[7].trim() : '';
            let opcion1 = '';
            let opcion2 = '';
            let opcion3 = '';
            let anchoIzq: number | undefined;
            let anchoCentro: number | undefined;
            let anchoDer: number | undefined;
            let espacioIzqCentro: number | undefined;
            let espacioCentroDer: number | undefined;
            let espFinal: number | undefined;
            let texto = rawTexto;

            if (tipo === 'pregunta') {
                const rawAnchoIzq = parts[9];
                const rawEsp1 = parts[10];
                const rawAnchoCentro = parts[11];
                const rawEsp2 = parts[12];
                const rawAnchoDer = parts[13];
                const rawEspFinal = parts[14];

                if (rawAnchoIzq && rawEsp1 && rawAnchoCentro && rawEsp2 && rawAnchoDer && rawEspFinal !== undefined) {
                    const ai = parseInt(rawAnchoIzq.trim(), 10);
                    const e1 = parseInt(rawEsp1.trim(), 10);
                    const ac = parseInt(rawAnchoCentro.trim(), 10);
                    const e2 = parseInt(rawEsp2.trim(), 10);
                    const ad = parseInt(rawAnchoDer.trim(), 10);
                    const ef = parseInt(rawEspFinal.trim(), 10) || 0;

                    if (!isNaN(ai) && !isNaN(e1) && !isNaN(ac) && !isNaN(e2) && !isNaN(ad)) {
                        if (ai + e1 + ac + e2 + ad + ef === maxChars) {
                            anchoIzq = ai;
                            espacioIzqCentro = e1;
                            anchoCentro = ac;
                            espacioCentroDer = e2;
                            anchoDer = ad;
                            espFinal = ef;

                            const rawOpcion1 = parts[15];
                            const rawOpcion2 = parts[16];
                            const rawOpcion3 = parts[17];

                            if ((rawOpcion1 !== undefined && rawOpcion1.trim() !== '') || 
                                (rawOpcion2 !== undefined && rawOpcion2.trim() !== '') || 
                                (rawOpcion3 !== undefined && rawOpcion3.trim() !== '')) {
                                opcion1 = rawOpcion1 || '';
                                opcion2 = rawOpcion2 || '';
                                opcion3 = rawOpcion3 || '';
                            } else {
                                const unformatted = decodificarTextoPregunta(texto, anchoIzq, espacioIzqCentro, anchoCentro, espacioCentroDer, anchoDer, espFinal, maxChars, '@');
                                opcion1 = unformatted.opcion1;
                                opcion2 = unformatted.opcion2;
                                opcion3 = unformatted.opcion3;
                            }
                        }
                    }
                }
            }

            data.push({
                historia: parts[0] !== undefined ? parts[0].trim() : '',
                id: parts[1] !== undefined ? parts[1].trim() : `Screen_${i}`,
                texto,
                tyOffset,
                maxChars,
                primer_kanji: parts[5] !== undefined ? parts[5].trim() : '',
                ultimo_kanji: parts[6] !== undefined ? parts[6].trim() : '',
                tipo,
                revisado: parts[8] !== undefined ? parts[8].trim() : '',
                opcion1,
                opcion2,
                opcion3,
                opcion1Raw: parts[15],
                opcion2Raw: parts[16],
                opcion3Raw: parts[17],
                ruta_ref: parts[18],
                produce_marca: parts[19],
                espera_marca: parts[20],
                anchoIzq,
                anchoCentro,
                anchoDer,
                espacioIzqCentro,
                espacioCentroDer,
                espFinal
            });
        }
    }
    
    if (data.length === 0) {
      return { screens: [], error: 'El CSV no tiene filas válidas o no separa con punto y coma (;)' };
    }
    
    return { screens: data };
  } catch (e: any) {
    return { screens: [], error: e.message };
  }
}

export const DEFAULT_PREGUNTA_LAYOUT = {
  anchoIzq: 3,
  anchoCentro: 3,
  anchoDer: 3,
  espacioIzqCentro: 0,
  espacioCentroDer: 1,
  espFinal: 0,
};

export function getPreguntaLayout(screen: import('./types').ScreenData) {
  return {
    anchoIzq: screen.anchoIzq ?? DEFAULT_PREGUNTA_LAYOUT.anchoIzq,
    anchoCentro: screen.anchoCentro ?? DEFAULT_PREGUNTA_LAYOUT.anchoCentro,
    anchoDer: screen.anchoDer ?? DEFAULT_PREGUNTA_LAYOUT.anchoDer,
    espacioIzqCentro: screen.espacioIzqCentro ?? DEFAULT_PREGUNTA_LAYOUT.espacioIzqCentro,
    espacioCentroDer: screen.espacioCentroDer ?? DEFAULT_PREGUNTA_LAYOUT.espacioCentroDer,
    espFinal: screen.espFinal ?? DEFAULT_PREGUNTA_LAYOUT.espFinal,
  };
}

export function formatCSV(screens: import('./types').ScreenData[]): string {
    const header = "historia;pantalla;texto;ty_offset;max_chars;primer_kanji;ultimo_kanji;tipo;revisado;ancho_izq;esp_izq_centro;ancho_centro;esp_centro_der;ancho_der;esp_final;opcion1_raw;opcion2_raw;opcion3_raw;ruta_ref;produce_marca;espera_marca\n";
    const body = screens.map(s => {
      let finalTexto = s.texto;
      let aIzq = s.anchoIzq ?? "";
      let eIzqCen = s.espacioIzqCentro ?? "";
      let aCen = s.anchoCentro ?? "";
      let eCenDer = s.espacioCentroDer ?? "";
      let aDer = s.anchoDer ?? "";
      let eFin = s.espFinal ?? "";
      let o1Raw = "";
      let o2Raw = "";
      let o3Raw = "";
      let rutaRef = s.ruta_ref !== undefined ? s.ruta_ref : "";
      let produceMarca = s.produce_marca !== undefined ? s.produce_marca : "";
      let esperaMarca = s.espera_marca !== undefined ? s.espera_marca : "";

      if (s.tipo === 'pregunta') {
        const layout = getPreguntaLayout(s);
        
        aIzq = layout.anchoIzq;
        eIzqCen = layout.espacioIzqCentro;
        aCen = layout.anchoCentro;
        eCenDer = layout.espacioCentroDer;
        aDer = layout.anchoDer;
        eFin = layout.espFinal;
        
        o1Raw = s.opcion1 || "";
        o2Raw = s.opcion2 || "";
        o3Raw = s.opcion3 || "";

        if ((layout.anchoIzq + layout.espacioIzqCentro + layout.anchoCentro + layout.espacioCentroDer + layout.anchoDer + layout.espFinal) === s.maxChars) {
          finalTexto = formatearTextoPregunta(
            s.opcion2 || '', 
            s.opcion1 || '', 
            s.opcion3 || '', 
            layout.anchoIzq,
            layout.anchoCentro,
            layout.anchoDer,
            layout.espacioIzqCentro,
            layout.espacioCentroDer,
            layout.espFinal,
            '@'
          );
        }
      }
      
      return `${s.historia};${s.id};${finalTexto};${s.tyOffset};${s.maxChars};${s.primer_kanji};${s.ultimo_kanji};${s.tipo};${s.revisado};${aIzq};${eIzqCen};${aCen};${eCenDer};${aDer};${eFin};${o1Raw};${o2Raw};${o3Raw};${rutaRef};${produceMarca};${esperaMarca}`;
    }).join('\n');
    return header + body;
}
