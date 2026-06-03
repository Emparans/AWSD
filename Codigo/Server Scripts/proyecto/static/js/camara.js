window.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById("stream-camara");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/control/video_client`;
    
    let ws;

    function conectarWebSocket() {
        ws = new WebSocket(wsUrl);

        ws.onmessage = async (event) => {
            try {
                // 1. Convertimos el string base64 que llega en un Blob binario limpio
                const res = await fetch("data:image/jpeg;base64," + event.data);
                const blob = await res.blob();

                // 2. Decodificamos la imagen directamente en la GPU (No bloquea el navegador)
                const imageBitmap = await createImageBitmap(blob);

                // 3. Ajustamos el tamaño del canvas al del fotograma real si cambia
                if (canvas.width !== imageBitmap.width || canvas.height !== imageBitmap.height) {
                    canvas.width = imageBitmap.width;
                    canvas.height = imageBitmap.height;
                }

                // 4. Dibujamos instantáneamente y liberamos la memoria inmediatamente
                ctx.drawImage(imageBitmap, 0, 0);
                imageBitmap.close(); // Borra el frame de la memoria RAM al instante

            } catch (err) {
                console.debug("Error procesando frame:", err);
            }
        };

        ws.onclose = () => {
            console.log("Conexión de cámara perdida. Reconectando en 2 segundos...");
            setTimeout(conectarWebSocket, 2000);
        };

        ws.onerror = (error) => {
            console.error("Error en WebSocket de cámara:", error);
            ws.close();
        };
    }

    // Arrancamos la conexión inicial
    conectarWebSocket();
});