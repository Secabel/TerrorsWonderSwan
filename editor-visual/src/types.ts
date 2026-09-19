export interface ScreenData {
  historia: string;
  id: string;
  texto: string;
  tyOffset: number;
  maxChars: number;
  primer_kanji: string;
  ultimo_kanji: string;
  tipo: string;
  revisado: string;
  opcion1?: string;
  opcion2?: string;
  opcion3?: string;
  opcion1Raw?: string;
  opcion2Raw?: string;
  opcion3Raw?: string;
  ruta_ref?: string;
  produce_marca?: string;
  espera_marca?: string;
  anchoIzq?: number;
  anchoCentro?: number;
  anchoDer?: number;
  espacioIzqCentro?: number;
  espacioCentroDer?: number;
  espFinal?: number;
}

export interface Tile {
  tx: number;
  ty: number;
  c: string;
}

export interface LayoutResult {
  tiles: Tile[];
  horizontalCut: boolean;
  verticalCut: boolean;
  cutHorizontalText: string[];
  cutVerticalText: string[];
  invalidChars: string[];
  usedCols: number;
  maxCols: number;
}
