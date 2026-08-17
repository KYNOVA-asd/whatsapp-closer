# WhatsApp Web Explorer

Esta rama explora una idea distinta al blueprint principal: usar una sesion ya iniciada de
WhatsApp Web como superficie local para leer chats, preparar respuestas y operar un mini CRM de
ventas. No reemplaza la integracion formal con WhatsApp Cloud API; es un prototipo para entender
el flujo y validar si sirve para el negocio.

## Dificultad y riesgos

- **Scraper/lector de chats:** dificultad media.
- **Enviar mensajes desde WhatsApp Web:** dificultad media-alta, porque WhatsApp cambia selectores
  y puede detectar automatizacion.
- **ADB con WhatsApp movil:** posible, pero mas fragil todavia; sirve para prototipo, no es la
  opcion preferida para negocio.
- **Vendedor IA encima:** viable si primero estan bien definidos entrada/salida, historial y
  aprobacion humana.

## Lo que se puede construir en esta rama

## Iniciar WhatsApp Web con Edge local

Para probar con tu propia sesion sin mezclarla con tu navegador normal, esta rama usa un perfil
separado de Microsoft Edge. El perfil se guarda en `.local/edge-whatsapp-profile/` y queda
ignorado por git porque puede contener cookies y datos de sesion.

Hay una carpeta de ejemplo versionada en `.local-example/` para documentar la estructura sin
guardar datos reales.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\abrir_whatsapp_web_edge.ps1
```

Al abrirse Edge, escanea el QR desde tu telefono. La proxima vez que ejecutes el mismo comando,
WhatsApp Web deberia recordar la sesion mientras el telefono y WhatsApp mantengan el dispositivo
vinculado.

## Abrir la demo con interfaz Python

La rama tambien trae un panel local de escritorio para explorar el producto antes de construir el
scraper real. El panel abre WhatsApp Web con Edge, muestra una bandeja CRM demo, importa CSV,
genera borradores y simula una cola de envio.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\abrir_panel_whatsapp_web.ps1
```

Tambien se puede abrir directo:

```powershell
python scripts\whatsapp_web_explorer_app.py
```

### Prueba real controlada: chat activo

El panel incluye dos botones experimentales:

- **Leer chat activo:** lee solamente el chat que este abierto en WhatsApp Web.
- **Responder hola mundo:** envia `hola mundo` solamente al chat activo y pide confirmacion antes.

Para que funcionen, abre WhatsApp Web con el script de esta rama. Ese script levanta Edge con
debug local en `127.0.0.1:9222`; el bridge no se conecta a tu navegador normal ni lee perfiles
fuera de `.local/edge-whatsapp-profile/`.

Si Edge ya estaba abierto antes de agregar el debug local, reinicia solo el perfil de esta rama:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\reiniciar_whatsapp_web_edge.ps1
```

Tambien puedes probarlo por terminal:

```powershell
python scripts\whatsapp_web_bridge.py read
python scripts\whatsapp_web_bridge.py send --text "hola mundo"
```

### Monitor local de WhatsApp Web

Lee chats visibles, contacto, ultimo mensaje y estado, y lo guarda localmente para poder revisar
la bandeja sin depender de una API oficial.

### Panel CRM local

Lista leads con etapa, resumen, ultimo mensaje y pendiente de responder. La idea es convertir los
chats en una bandeja de trabajo, no solo en conversaciones sueltas.

### Generador de respuestas

La IA sugiere respuestas segun catalogo, playbook e historial. Por defecto quedan en borrador para
que una persona las revise antes de enviar.

### Envio controlado

Solo para contactos propios o importados con consentimiento o relacion previa. Esta rama no busca
construir spam masivo a numeros frios ni mecanismos para evadir bloqueos.

### CSV tipo RocketSend, pero sano

Importa contactos o clientes desde CSV, personaliza mensajes con variables como `{nombre}` y
`{producto}`, y ayuda a preparar campanas con limites, opt-out y revision antes del envio.

## Criterio de producto

El objetivo es una herramienta de ventas prudente sobre WhatsApp Web: leer, ordenar, sugerir,
aprobar y dar seguimiento. Para produccion real, la ruta mas estable sigue siendo Meta WhatsApp
Cloud API o un proveedor como Zernio, porque dan webhooks, firmas, trazabilidad y menos fragilidad
operativa.
