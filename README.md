# Dashboard Comportamental

## Configuración antes de desplegar

1. Sube `datos.csv` a Google Drive y copia el File ID de la URL
2. En `app.py` reemplaza `REEMPLAZA_CON_TU_FILE_ID` con tu ID real
3. Haz el archivo **público** en Google Drive (cualquiera con el enlace puede ver)

## Despliegue en Render

1. Sube esta carpeta a un repositorio GitHub
2. Ve a render.com → New → Web Service
3. Conecta el repositorio
4. Render detecta el `render.yaml` automáticamente
5. Haz clic en Deploy

## Uso local

```bash
pip install -r requirements.txt
python3 app.py
```
