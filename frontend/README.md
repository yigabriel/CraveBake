# Crave Bake — Frontend

React 18 + Vite + TypeScript + Tailwind (tokens del design system "Pastry" de Stitch) + TanStack Query + react-i18next.

## Correr en local

```bash
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000/v1
npm install
npm run dev                  # http://localhost:5173
```

El backend tiene que permitir `http://localhost:5173` en `CORS_ALLOWED_ORIGINS`.

## Scripts

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo |
| `npm run build` | Chequeo de tipos + build de producción en `dist/` |
| `npm test` | Tests unitarios (escalado/redondeo de cantidades, comparación de versiones) |

## Estructura

- `src/api/` — cliente HTTP (formato único de errores, 401 → login), endpoints y tipos que replican los schemas del backend.
- `src/pages/` — una pantalla por archivo (Explorar, Detalle, Editor, Portafolio, Swipe, Modo cocina, Perfil, Despensa, Mi cocina, Historial, Conversor, Login/Registro).
- `src/lib/` — lógica pura: cantidades con `decimal.js`, tiempos, comparación de versiones, alarma de temporizador.
- `src/i18n/` — textos en `es` y `en` (`en` está tipado contra `es`: una clave faltante rompe el build).

Las reglas de negocio que el front debe respetar están en [docs/FRONTEND_FEATURES.md](../docs/FRONTEND_FEATURES.md).
