const ws = new WebSocket("ws://" + window.location.host + "/ws");

// Funció per sol·licitar una pregunta al servidor (s'envia un missatge de text)
function solicitarPregunta() {
    // Li enviem al servidor la senyal per a que seleccioni una pregunta a l'atzar
    ws.send("pedir_pregunta");
}

// Controlador d'esdeveniments quan arriba un missatge del servidor via WebSocket
ws.onmessage = (event) => {
    const paquete = JSON.parse(event.data); // Suposa que el missatge és JSON
    if (paquete.accion === "mostrar_pregunta") {
        // Mostra la capa/pantalla de la pregunta
        document.getElementById("pantalla-pregunta").style.display = "block";
        // Insereix el text de la pregunta a l'element corresponent
        document.getElementById("texto-pregunta").innerText = paquete.datos.pregunta;
        
        // Neteja el contenidor d'opcions i afegeix nous botons (una opció per resposta)
        const container = document.getElementById("opciones-container");
        container.innerHTML = "";
        paquete.datos.opciones.forEach(opcion => {
            container.innerHTML += `<button>${opcion}</button>`;
        });
    }
};

// Funció asíncrona per llegir el contingut d'un arxiu via HTTP GET
async function leerTexto() {
    // Fa una petició GET a "/leerArchivo"
    const respuesta = await fetch("/leerArchivo");
    const datos = await respuesta.json(); // Convertim la resposta a objecte
    
    if (datos.contenido) {
        // Mostra el contingut a l'element amb id "contenido_texto"
        document.getElementById("contenido_texto").innerText = datos.contenido;
    }
    else{
        // Si no hi ha "contenido", mostra l'error
        alert(datos.error);
    }
}