# WebUI (Svelte + Vite)

## Desarrollo

```bash
cd webui
npm install
npm run dev
```

Luego inicia la app Python con:

```bash
python3 organizador_multimedia.py
```

Por defecto intenta cargar `http://127.0.0.1:5173`.

## Producción

```bash
cd webui
npm install
npm run build
```

La app Python cargará automáticamente `webui/dist/index.html` si existe.
