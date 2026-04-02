# Integración en Fedora KDE (menú, autostart, actualizaciones)

## 1. Dependencias (una vez)

En el clon del repositorio:

```bash
cd "/ruta/a/Organizador Fedora KDE"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[qt]"
```

`[qt]` instala PyQt6 + WebEngine (lo que ya usas con `ORGANIZADOR_PREFER_QT=1`).

## 2. Entrada en el menú y opcionalmente al iniciar sesión

```bash
./scripts/install-desktop-kde.sh
./scripts/install-desktop-kde.sh --autostart   # además: arranque al login
```

Se crea `~/.local/share/applications/org.nanrroti.galeria-ayn.desktop`.  
Con `--autostart` se copia también a `~/.config/autostart/`.

El `.desktop` ejecuta `env -C <repo> scripts/organizador-launch.sh` (directorio de trabajo absoluto; evita el error de Plasma «WorkingDirectory= expects an absolute path»). El script fija `ORGANIZADOR_PREFER_QT=1` y lanza `python3 -m org_multimedia`.

## 3. Comando global `organizador` (opcional)

Con el venv activado:

```bash
pip install -e ".[qt]"
```

Quedará un ejecutable `organizador` (normalmente en `~/.local/bin/`).  
Puedes lanzar desde terminal: `organizador` (sin variable de entorno extra; `prepare_linux_gui_env` sigue respetando `ORGANIZADOR_PREFER_QT` si la exportas).

Para que el menú use ese comando en lugar del script, edita el `.desktop` y cambia la línea `Exec=` por:

`Exec=env ORGANIZADOR_PREFER_QT=1 /ruta/a/.venv/bin/organizador`

## 4. Cómo actualizar el programa

1. `git pull`
2. Si tocaste la interfaz web: `cd webui && npm ci && npm run build`
3. Si cambiaron dependencias Python: `pip install -e ".[qt]"` (con el mismo venv)

No hace falta reinstalar el `.desktop` mientras no muevas la carpeta del repositorio. Si mueves el clon, vuelve a ejecutar `install-desktop-kde.sh`.

## 5. Quitar autostart o el acceso del menú

- Autostart: borra `~/.config/autostart/org.nanrroti.galeria-ayn.desktop`
- Menú: borra `~/.local/share/applications/org.nanrroti.galeria-ayn.desktop` y ejecuta `update-desktop-database ~/.local/share/applications` si existe el comando
