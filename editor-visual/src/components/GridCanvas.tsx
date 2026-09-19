import React, { useEffect, useRef } from 'react';
import { LayoutResult } from '../types';
import { FONT_JSON } from '../font';

interface GridCanvasProps {
  layout: LayoutResult;
}

export const GridCanvas: React.FC<GridCanvasProps> = ({ layout }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Canvas settings
    const CELL_SIZE = 8; // 8x8 pixel internal grid
    const SCALE = 4; // Render scale to make it nice and chunky
    const TOTAL_CELLS = 16;
    const PIXEL_SIZE = CELL_SIZE * SCALE; // 32px per cell
    const CANVAS_SIZE = TOTAL_CELLS * PIXEL_SIZE; // 512px

    canvas.width = CANVAS_SIZE;
    canvas.height = CANVAS_SIZE;

    // High Density Color Palette
    const COLOR_BG = '#0f1012';    // theme-bg
    const COLOR_GRID = '#374151';  // theme-border
    const COLOR_PIXEL = '#00ff88'; // theme-accent

    // Clear background
    ctx.fillStyle = COLOR_BG;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = COLOR_GRID;
    
    for (let i = 0; i <= TOTAL_CELLS; i++) {
        const offset = i * PIXEL_SIZE;
        // Verticals
        ctx.beginPath();
        ctx.moveTo(offset, 0);
        ctx.lineTo(offset, CANVAS_SIZE);
        ctx.stroke();
        // Horizontals
        ctx.beginPath();
        ctx.moveTo(0, offset);
        ctx.lineTo(CANVAS_SIZE, offset);
        ctx.stroke();
    }

    // Render characters
    ctx.fillStyle = COLOR_PIXEL;
    
    for (const tile of layout.tiles) {
      if (tile.c === '  ' || tile.c === ' ' || tile.c === '@') continue; // Skip space rendering
      const fontDef = FONT_JSON[tile.c];
      
      if (fontDef) {
        // Base mapping:
        // tx, ty is the top-left coordinate of the 8x8 tile.
        const basePxX = tile.tx * PIXEL_SIZE;
        const basePxY = tile.ty * PIXEL_SIZE;

        // Font is 5x5, embedded in an 8x8 tile with ~1.5px padding.
        // Let's offset by 1 or 2 logical units (scale px) down and right
        const OFFSET_X = 1 * SCALE;
        const OFFSET_Y = 1 * SCALE;

        for (let y = 0; y < 5; y++) {
          for (let x = 0; x < 5; x++) {
            if (fontDef[y][x] === 1) {
                // Notice we do NOT apply any coordinate transformation or rotation here.
                // It draws left-to-right, top-to-bottom within the local cell, normal reading.
                ctx.fillRect(
                  basePxX + OFFSET_X + x * SCALE,
                  basePxY + OFFSET_Y + y * SCALE,
                  SCALE,
                  SCALE
                );
            }
          }
        }
      }
    }

  }, [layout]);

  return (
    <div className="relative group overflow-hidden bg-theme-bg">
      <canvas 
        ref={canvasRef} 
        style={{ width: '100%', aspectRatio: '1/1', imageRendering: 'pixelated' }}
        className="block mx-auto cursor-crosshair"
      />
      {/* Overlay coordinate labels (show on hover) */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <span className="absolute top-1 left-2 text-[10px] text-theme-accent font-mono font-bold bg-theme-bg/80 px-1 rounded border border-theme-border">tx=0, ty=0</span>
        <span className="absolute bottom-1 right-2 text-[10px] text-theme-accent font-mono font-bold bg-theme-bg/80 px-1 rounded border border-theme-border">tx=15, ty=15</span>
      </div>
    </div>
  );
};
