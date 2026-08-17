# .local example

Esta carpeta muestra la estructura local esperada para los prototipos de `whatsapp-web-explorer`.
No contiene datos reales, cookies ni sesiones.

La carpeta real se llama `.local/` y esta ignorada por git.

## Estructura

```text
.local/
  edge-whatsapp-profile/
    ...perfil persistente de Microsoft Edge...
```

`edge-whatsapp-profile/` guarda la sesion de WhatsApp Web despues de escanear el QR. Esa carpeta
puede contener cookies, local storage y otros datos sensibles, por eso nunca debe versionarse.

Para crearla y abrir WhatsApp Web:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\abrir_whatsapp_web_edge.ps1
```

Para probar la importacion desde la interfaz Python, usa `contactos-demo.csv`.

`config.example.json` muestra los valores locales esperados para limites, pausas, opt-out y LLM
local.
