window.addEventListener('DOMContentLoaded', () => {
    const img = document.getElementById("stream-camara");
    if (!img) {
        console.error("No se encontró el elemento #stream-camara en el HTML");
        return;
    }
    
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${window.location.host}/ws/viewer`;
    
    let ws;

    function conectarWebSocket() {
        console.log("Intentando conectar al WebSocket de la cámara...");
        ws = new WebSocket(wsUrl);
        ws.binaryType = 'blob';

        ws.onopen = () => {
            console.log("¡Conectado con éxito al streaming de la cámara!");
        };

        ws.onmessage = (event) => {
            console.log("Fotograma recibido del backend. Tamaño (bytes):", event.data.size);
            
            const nuevaUrl = URL.createObjectURL(event.data);
            const viejaUrl = img.src;
            
            img.onload = () => {
                if (viejaUrl && viejaUrl.startsWith('blob:')) {
                    URL.revokeObjectURL(viejaUrl);
                }
            };
            
            img.src = nuevaUrl;
        };

        ws.onclose = (e) => {
            console.log("Conexión de video cerrada:", e.reason, "Reconectando en 2s...");
            setTimeout(conectarWebSocket, 2000);
        };

        ws.onerror = (error) => {
            console.error("Error en WebSocket de video:", error);
            ws.close();
        };
    }

    conectarWebSocket();
});