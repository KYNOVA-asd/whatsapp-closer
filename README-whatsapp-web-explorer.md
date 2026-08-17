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
