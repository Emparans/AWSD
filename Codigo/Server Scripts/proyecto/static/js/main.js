const ws = new WebSocket("ws://" + window.location.host + "/ws");

    function solicitarPregunta() {
        // Le enviamos al servidor la señal para que elija una al azar
        ws.send("pedir_pregunta");
    }

    ws.onmessage = (event) => {
        const paquete = JSON.parse(event.data);
        if (paquete.accion === "mostrar_pregunta") {
            document.getElementById("pantalla-pregunta").style.display = "block";
            document.getElementById("texto-pregunta").innerText = paquete.datos.pregunta;
            
            // Limpiamos opciones anteriores y creamos nuevas
            const container = document.getElementById("opciones-container");
            container.innerHTML = "";
            paquete.datos.opciones.forEach(opcion => {
                container.innerHTML += `<button>${opcion}</button>`;
            });
        }
    };


async function leerTexto() {
    // Hacemos la petición HTTP a nuestra nueva ruta
    const respuesta = await fetch("/leerArchivo");
    const datos = await respuesta.json(); // Convertimos la respuesta a objeto
    
    if (datos.contenido) {
        document.getElementById("contenido_texto").innerText = datos.contenido;
    }
    else{
        alert(datos.error);
    }
}