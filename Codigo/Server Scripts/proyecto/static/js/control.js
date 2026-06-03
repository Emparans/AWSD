import { dibujarTodoElMapa } from './motorDibujo.js';

// Assets de imágenes
const imagenes = { tileset: new Image(), player: new Image(), doors: new Image(), keys: new Image(), poi: new Image() };
const cargarImagen = (img, src) => new Promise(res => { img.onload = () => res(img); img.src = src; });

// Variables de control y DOM
let mapaGlobal = null;
const el = { puntuacion: null, tiempo: null, nivel: null };

async function pedirData() {
    try {
        const respuesta = await fetch(`/control/obtenerMapa?t=${Date.now()}`);
        if (!respuesta.ok) throw new Error(respuesta.statusText);
        return await respuesta.json();
    } catch (e) { console.error("Error al pedir mapa:", e); }
}

function actualizarPanel(puntuacion, tiempo, nivel) {
    if (el.puntuacion) el.puntuacion.textContent = puntuacion;
    if (el.tiempo) el.tiempo.textContent = tiempo;
    if (el.nivel) el.nivel.textContent = nivel;
}

window.addEventListener('DOMContentLoaded', async () => {
    const canvas = document.getElementById('juego');
    const ctx = canvas.getContext('2d');
    
    el.puntuacion = document.getElementById("dato-puntuacion");
    el.tiempo = document.getElementById("dato-tiempo");
    el.nivel = document.getElementById("dato-nivel");

    // Carga de datos y recursos en paralelo
    const [data] = await Promise.all([
        pedirData(),
        cargarImagen(imagenes.player, "/static/sprites/player.png"),
        cargarImagen(imagenes.tileset, '/static/sprites/tileset.png'),
        cargarImagen(imagenes.doors, "/static/sprites/doors.png"),
        cargarImagen(imagenes.poi, "/static/sprites/poi.png"),
        cargarImagen(imagenes.keys, "/static/sprites/keys.png")
    ]);

    if (!data) return console.error("No se pudieron obtener los datos de control.");
    
    mapaGlobal = data;
    dibujarTodoElMapa(canvas, ctx, mapaGlobal, imagenes);
    if (mapaGlobal.state) actualizarPanel(mapaGlobal.state.score, "00:00", mapaGlobal.state.remainingQuests);

    iniciarWebSocket(canvas, ctx);
});

function iniciarWebSocket(canvas, ctx) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsCliente = new WebSocket(`${wsProtocol}//${window.location.host}/control/client`);
    let isFetching = false;

    wsCliente.onmessage = async (event) => {
        try {
            const mensaje = JSON.parse(event.data);
            if (!mensaje.tempPos || !mapaGlobal) return;

            // Actualizar posición del robot directamente
            mapaGlobal.robot.currentPos = mensaje.tempPos;
            mapaGlobal.robot.currentDir = mensaje.tempDir;

            // Si se requiere actualización completa de la lógica del mapa desde el backend
            if ((mensaje.update_map || mensaje.change) && !isFetching) {
                isFetching = true;
                const nuevoMapa = await pedirData();
                if (nuevoMapa) {
                    mapaGlobal.nodes = nuevoMapa.nodes;
                    mapaGlobal.pois = nuevoMapa.pois;
                    if (nuevoMapa.state) actualizarPanel(nuevoMapa.state.score, "00:00", nuevoMapa.state.remainingQuests);
                }
                isFetching = false;
            }
            dibujarTodoElMapa(canvas, ctx, mapaGlobal, imagenes);
        } catch (e) { console.error("Error WebSocket mensaje:", e); }
    };

    wsCliente.onclose = () => setTimeout(() => iniciarWebSocket(canvas, ctx), 2000);
    wsCliente.onerror = () => wsCliente.close();
}

// =========================================
// LÓGICA DEL POP-UP (MANTENIDA Y COMPACTADA)
// =========================================
window.abrirPopUp = () => {  document.getElementById('inputNombre').value = ""; document.getElementById('capaFondo').style.display = 'flex'; };
window.cerrarPopUp = () => { document.getElementById('capaFondo').style.display = 'none'; };

window.enviarDatos = async () => {
    const nombre = document.getElementById('inputNombre').value.trim();
    const creador = document.getElementById('inputCreador').value.trim();
    
    if (!nombre) return alert("¡El nombre no puede estar vacío!");
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