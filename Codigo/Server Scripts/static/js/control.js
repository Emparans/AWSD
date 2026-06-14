// Importa el motor de dibuix del mapa
import { dibujarTodoElMapa } from './motorDibujo.js';

// Assets d'imatges
const imagenes = { tileset: new Image(), player: new Image(), player_star: new Image(), player_cloud: new Image(), player_moon: new Image(), player_sun: new Image(), doors: new Image(), keys: new Image(), poi: new Image() };
// Funció auxiliar per carregar una imatge
const cargarImagen = (img, src) => new Promise(res => { img.onload = () => res(img); img.src = src; });

let mapaGlobal = null;
const el = { puntuacion: null, tiempo: null, llave: -1 };
//let popUpAbierto = false;
let timeoutPregunta = null;

async function pedirData() {
    // Obté l'estat actual del mapa des del servidor
    try {
        const respuesta = await fetch(`/control/obtenerMapa?t=${Date.now()}`);
        if (!respuesta.ok) throw new Error(respuesta.statusText);
        return await respuesta.json();
    } catch (e) { console.error("Error al pedir mapa:", e); }
}

function actualizarPanel(puntuacion, tiempo, llave) {
    // Actualitza el panell lateral amb la puntuació, temps i l'objecte que porta el robot (clau)
    if (el.puntuacion) el.puntuacion.textContent = puntuacion;
    if (el.tiempo) el.tiempo.textContent = formatearSegundos(tiempo);
    if (el.llave) {
        const nombresLlaves = {
            "-1": "Nada",
            "0": "Estrella",
            "1": "Nube",
            "2": "Luna",
            "3": "Sol"
        };
        el.llave.textContent = nombresLlaves[llave]
    }
}

let segundosTranscurridos = 0;
let cronometro;

// Inicia o reanuda el cronòmetre
function iniciarCronometro() {
    if (cronometro) clearInterval(cronometro); // Evitar duplicats
    cronometro = setInterval(() => {
        segundosTranscurridos++;
        if (el.tiempo) el.tiempo.textContent = formatearSegundos(segundosTranscurridos);
    }, 1000);
}

// Pausa el cronòmetre (guarda el temps actual)
function pausarCronometro() {
    clearInterval(cronometro);
}

// Reinicia el cronòmetre a 0 y el torna a arrancar
function reiniciarCronometro() {
    segundosTranscurridos = 0;
    if (el.tiempo) el.tiempo.textContent = "00:00";
    iniciarCronometro();
}

function formatearSegundos(segundosTotales) {
    const minutos = Math.floor(segundosTotales / 60);
    const segundos = segundosTotales % 60;
    return `${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
}

window.addEventListener('DOMContentLoaded', async () => {
    const canvas = document.getElementById('juego');
    const ctx = canvas.getContext('2d');
    
    // Referències als elements del DOM
    el.puntuacion = document.getElementById("dato-puntuacion");
    el.tiempo = document.getElementById("dato-tiempo");
    el.llave = document.getElementById("dato-objeto");

    // Carrega dades i imatges en paral·lel
    const [data] = await Promise.all([
        pedirData(),
        cargarImagen(imagenes.player, "/static/sprites/player.png"),
        cargarImagen(imagenes.tileset, '/static/sprites/tileset.png'),
        cargarImagen(imagenes.doors, "/static/sprites/doors.png"),
        cargarImagen(imagenes.poi, "/static/sprites/poi.png"),
        cargarImagen(imagenes.keys, "/static/sprites/keys.png"),
        cargarImagen(imagenes.player_star, "/static/sprites/player_star.png"),
        cargarImagen(imagenes.player_cloud, "/static/sprites/player_cloud.png"),
        cargarImagen(imagenes.player_moon, "/static/sprites/player_moon.png"),
        cargarImagen(imagenes.player_sun, "/static/sprites/player_sun.png")
    ]);

    if (!data) return console.error("No se pudieron obtener los datos de control");
    
    mapaGlobal = data;
    //dibujarTodoElMapa(canvas, ctx, mapaGlobal, imagenes);
    if (mapaGlobal.state) actualizarPanel(0, 0, -1);

    // Arranca el cronòmetre al carregar la partida
    iniciarCronometro();

    // Estableix la connexió WebSocket per rebre actualitzacions en temps real
    iniciarWebSocket(canvas, ctx);
});

function iniciarWebSocket(canvas, ctx) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsCliente = new WebSocket(`${wsProtocol}//${window.location.host}/control/client`);
    let isFetching = false;

    wsCliente.onmessage = async (event) => {
        try {
            const mensaje = JSON.parse(event.data);

            if (mensaje.pregunta) {
                window.mostrarPregunta(mensaje.pregunta);
                return;
            }

            if (!mensaje.tempPos || !mapaGlobal) return;

            mapaGlobal.robot.currentPos = mensaje.tempPos;
            mapaGlobal.robot.currentDir = mensaje.tempDir;
            
            if (mensaje.reinicio_crono)
            {
                reiniciarCronometro()
            }

            if ((mensaje.update_map || mensaje.change) && !isFetching) {
                isFetching = true;
                const nuevoMapa = await pedirData();
                if (nuevoMapa) {
                    mapaGlobal.nodes = nuevoMapa.nodes;
                    mapaGlobal.pois = nuevoMapa.pois;
                    mapaGlobal.robot.held = nuevoMapa.robot.held
                    if (nuevoMapa.state) actualizarPanel(nuevoMapa.state.score, segundosTranscurridos, mapaGlobal.robot.held);
                }
                isFetching = false;
            }
            dibujarTodoElMapa(canvas, ctx, mapaGlobal, imagenes);
        } catch (e) { console.error("Error WebSocket mensaje:", e); }
    };

    wsCliente.onclose = () => setTimeout(() => iniciarWebSocket(canvas, ctx), 2000);
    wsCliente.onerror = () => wsCliente.close();
}

// Finestra "pop up" per guardar la informació de la partida
window.abrirPopUp = () => {  
    document.getElementById('inputNombre').value = ""; 
    document.getElementById('inputCreador').value = ""; 
    document.getElementById('capaFondo').style.display = 'flex'; 
    pausarCronometro(); // Pausar cronòmetre al obrir el popup
};
window.cerrarPopUp = () => { 
    document.getElementById('capaFondo').style.display = 'none'; 
    iniciarCronometro(); // Reanudar el cronòmetre al tancar el popup
};

window.enviarDatos = async () => {
    const nombre = document.getElementById('inputNombre').value.trim();
    const creador = document.getElementById('inputCreador').value.trim();

    if (!nombre) return alert("¡El nombre no puede estar vacío!");
    if (!creador) return alert("¡El nombre del creador no puede estar vacío!")
    cerrarPopUp();

    try {
        const res = await fetch('http://34.0.201.131:8080/historial/guardar', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, creador })
        });
        if (res.ok) alert("¡Datos guardados con éxito!");
    } catch (e) { console.error("Error de conexión:", e); }
};

window.chunks = [];
window.recorder = null;

window.mostrarPregunta = function(pregunta) {
    if (timeoutPregunta) {
        clearTimeout(timeoutPregunta);
        timeoutPregunta = null;
    }
    const contenedor = document.getElementById("contenedor_pregunta");
    if (contenedor) {
        contenedor.style.display = 'flex';
        contenedor.innerHTML = `
            <div class="panel preguntas-panel">
                <h3>${pregunta}</h3>
                <div class="barra-inferior" style="padding: 0; margin: 5px 0;">
                    <button class="btn" id="btn-record" onclick="toggleGrabacion(this)">🎤 Grabar</button>
                    <button class="btn" id="btn-send" onclick="enviarAudio(this)" disabled>📤 Enviar</button>
                    <button class="btn" id="btn-cancel" onclick="cancelarQR(this)">❌ Cancelar</button>
                </div>
                <div id="respuesta-vm" class="dato-valor" style="font-size: 1rem;"></div>
            </div>
        `;
    } else {
        console.error("No existe el div con id 'contenedor_pregunta'");
    }
};

window.toggleGrabacion = async function(btn) {
    if (!window.recorder || window.recorder.state === "inactive") {
        window.chunks = [];
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            window.recorder = new MediaRecorder(stream);
            window.recorder.ondataavailable = e => window.chunks.push(e.data);
            window.recorder.onstop = () => {
                document.getElementById("btn-send").disabled = false;
            };
            
            window.recorder.start();
            btn.innerHTML = "⏹️ Parar";
            btn.style.backgroundColor = "#ff4444";
            btn.style.color = "white";
        } catch(err) {
            console.error("Error accediendo al micrófono:", err);
            alert("No se pudo acceder al micrófono.");
        }
    } else {
        window.recorder.stop();
        btn.innerHTML = "🎤 Grabar";
        btn.style.backgroundColor = "";
        btn.style.color = "";
    }
};

window.enviarAudio = async function(btn) {
    btn.disabled = true;
    const respuestaDiv = document.getElementById("respuesta-vm");
    if (respuestaDiv) respuestaDiv.innerText = "⏳ Procesando respuesta con Gemini...";

    try {
        const res = await fetch("/control/procesar-audio", {
            method: "POST",
            body: new Blob(window.chunks, { type: 'audio/wav' })
        });

        const data = await res.json();

        if (data && data.texto) {
            if (respuestaDiv) {
                respuestaDiv.innerHTML = `
                    <div class="registro-transmision">
                        <div class="bloque-registro">
                            <div class="registro-cabecera">Usuario</div>
                            <div class="registro-cuerpo">${data.textoUsuario}</div>
                        </div>
                        <div class="bloque-registro alerta">
                            <div class="registro-cabecera">Respuesta gemini</div>
                            <div class="registro-cuerpo">${data.texto}</div>
                        </div>
                    </div>
                `;
            }          
            if (data.audio) {
                const audioUrl = `data:audio/wav;base64,${data.audio}`;
                const audio = new Audio(audioUrl);
                audio.play();
                audio.onended = () => {
                    timeoutPregunta = setTimeout(() => {
                        const contenedor = document.getElementById("contenedor_pregunta");
                        if (contenedor) contenedor.style.display = 'none';
                        timeoutPregunta = null; // Limpiamos la variable una vez ejecutado
                    }, 4000);
                };
            }
        } else {
            if (respuestaDiv) respuestaDiv.innerText = "Error formato de respuesta.";
        }

    } catch (err) {
        console.error("Error sending audio:", err);
        if (respuestaDiv) respuestaDiv.innerText = "Error conexión servidor.";
        btn.disabled = false; 
    }
};

window.cancelarQR = async function(btn) {
    const res = await fetch("/control/cancelarQR");
    const contenedor = document.getElementById("contenedor_pregunta");
    if (contenedor) contenedor.style.display = 'none';
};

// ---------- CONTROL DE PAUSA DEL ROBOT ----------
window.enviarPausa = async (estadoPausa) => {
    try {
        const res = await fetch(`/raspberry/pausar_robot?pausar=${estadoPausa}`, {
            method: 'POST'
        });

        if (res.ok) {
            const btnPausa = document.getElementById('btn-pausa');
            const btnReanudar = document.getElementById('btn-reanudar');

            if (estadoPausa) {
                btnPausa.style.display = 'none';
                btnReanudar.style.display = 'inline-block';
                pausarCronometro(); // CORRECCIÓN: Pausa el tiempo si pausas el robot
            } else {
                btnReanudar.style.display = 'none';
                btnPausa.style.display = 'inline-block';
                iniciarCronometro(); // CORRECCIÓN: Reanuda el tiempo al reanudar el robot
            }
        } else {
            console.error("El servidor devolvió error al intentar pausar.");
        }
    } catch (e) {
        console.error("Error de conexión al enviar orden de pausa:", e);
        alert("No se pudo comunicar con el robot.");
    }
};

// Exponer la función de reinicio globalmente por si quieres llamarla desde consola o algún botón nuevo
window.reiniciarCronometro = reiniciarCronometro;