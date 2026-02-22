# Guía de Despliegue en Vercel para Rubin Agente

Acabamos de adaptar el código para que sea compatible con el entorno **Serverless (sin servidor) de Vercel**, el cual es ideal (y totalmente **gratuito**) para este tipo de bots. 

Con este setup, Rubin no estara corriendo infinitamente consumiendo recursos, sino que Vercel lo "despertará" cada 12 horas, publicará un tweet y se volverá a apagar a los 5 segundos.

### Paso 1: Subir el código a GitHub
Es necesario que este proyecto esté en un repositorio de GitHub (público o privado, no importa). 
Abre una terminal en esta carpeta y corre:
```bash
git init
git add .
git commit -m "Vercel Migration"
```
Luego crea un repositorio en GitHub, y súbelo.

### Paso 2: Importar en Vercel
1. Ve a [vercel.com](https://vercel.com) e inicia sesión (puedes usar tu cuenta de GitHub).
2. Toca en **"Add New..." -> "Project"**.
3. Selecciona tu repositorio de GitHub que contiene este código y dale a **"Import"**.

### Paso 3: Variables de Entorno (CRÍTICO)
Antes de darle al botón final de **Deploy**, debes configurar tus variables de entorno para que Vercel pueda acceder a OpenAI y a X/Twitter.
1. En la misma pantalla de "Deploy", baja hasta la sección **Environment Variables**.
2. Copia y pega las siguientes variables que tienes en tu archivo `.env`:
   - `OPENAI_API_KEY`
   - `X_CONSUMER_KEY`
   - `X_CONSUMER_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
3. Dale al botón azul **"Deploy"**.

### Paso 4: ¡Dejarlo ser!
¡Y listo! Vercel detectará automáticamente nuestro archivo `vercel.json` y configurará un **Cron Job** (un temporizador) que llamará tu endpoint `api/cron` exactamente **cada 12 horas**. 

### (Opcional) Probar el Cron Manualmente
Si quieres forzar a Rubin a que postee inmediatamente para probar que la configuración está bien, puedes:
1. Ir al panel de control de tu proyecto en Vercel.
2. Ir a la pestaña **"Settings" > "Cron Jobs"**.
3. Verás la tarea `/api/cron` listada ahí. Haz clic en **"Run"** o abre directamente el link de tu dominio de vercel seguido de `/api/cron` (Ejemplo: `tusitio.vercel.app/api/cron`).
4. Verificá si se publicó el tweet.
