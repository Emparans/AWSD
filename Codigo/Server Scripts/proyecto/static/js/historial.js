import { dibujarTodoElMapa } from './motorDibujo.js';

const imagenes = {
    tileset: new Image(),
    player: new Image(),
    doors: new Image(),
    keys: new Image(),
    poi: new Image()
};

function cargarImagen(img, src) {
    return new Promise(resolve => {
        img.onload = () => resolve(img);
        img.src = src;
    });
}

async function cargarListaMapas() {
    const lista = document.getElementById('lista');
    const respuesta = await fetch('/historial/obtenerMapas').then(res => res.json());
    
    lista.innerHTML = respuesta.mapas.map(m => `
        <button class="btn-mapa-modular" onclick="verMapa('${m}')">
            ${m.replace('.json','').toUpperCase()}
        </button>
    `).join('');
}

window.addEventListener('DOMContentLoaded', async () => {
    const cargaRecursos = Promise.all([
        cargarImagen(imagenes.player, "/static/sprites/player.png"),
        cargarImagen(imagenes.tileset, '/static/sprites/tileset.png'),
        cargarImagen(imagenes.doors, "/static/sprites/doors.png"),
        cargarImagen(imagenes.poi, "/static/sprites/poi.png"),
        cargarImagen(imagenes.keys, "/static/sprites/keys.png")
    ]);

    await cargarListaMapas();
    await cargaRecursos;
});

window.verMapa = async function(nombreArchivo) {
    const visor = document.getElementById('visor');
    visor.innerHTML = "<div class='contenido-visor'>Cargando datos de GCS...</div>";

    const data = await fetch(`/historial/obtenerMapa/${nombreArchivo}`).then(res => res.json());

    if (data) {
        const tiempo = data.state.tiempo || "00:00";
        const puntos = data.state.score || 0;
        const nombreMapa = nombreArchivo.replace('.json', '').toUpperCase();

        visor.innerHTML = `
            <div class="visor-layout-modular">
                <div class="area-canvas">
                    <div class="canvas-container">
                        <canvas id="juego" width="500" height="500"></canvas>
                    </div>
                </div>
                <div class="area-datos-lateral">
                    <div class="sub-panel-info">
                        <div class="info-header">Nombre</div>
                        <div class="info-value highlight-blue">${nombreMapa}</div>
                    </div>

                    <div class="sub-panel-info">
                        <div class="info-header">Creador</div>
                        <div class="info-value highlight-blue">Nombre</div>
                    </div>

                    <div class="sub-panel-info">
                        <div class="info-header">Fecha</div>
                        <div class="info-value highlight-blue">Fecha</div>
                    </div>
                    
                    <div class="sub-panel-info">
                        <div class="info-header">Tiempo Registrado</div>
                        <div class="info-value">${tiempo}</div>
                    </div>
                    <div class="sub-panel-info">
                        <div class="info-header">Puntuación Total</div>
                        <div class="info-value highlight-green">${puntos} pts</div>
                    </div>

                    <button class="btn-eliminar-lateral" onclick="abrirPopUpEliminar('${nombreArchivo}')">
                        Eliminar Mapa
                    </button>
                </div>
            </div>
        `;

        const nuevoCanvas = document.getElementById('juego');
        const ctx = nuevoCanvas.getContext('2d');
        dibujarTodoElMapa(nuevoCanvas, ctx, data, imagenes);
    }
};

window.abrirPopUpEliminar = function(nombreArchivo) {
    document.getElementById('archivoAEliminar').value = nombreArchivo;
    document.getElementById('capaFondoEliminar').style.display = 'flex'; // El único cambio de estilo permitido por JS para mostrar el pop-up
};

window.cerrarPopUpEliminar = function() {
    document.getElementById('capaFondoEliminar').style.display = 'none';
};

window.confirmarEliminarDatos = async function() {
    const nombreArchivo = document.getElementById('archivoAEliminar').value;
    cerrarPopUpEliminar();

    try {
        const respuesta = await fetch(`/historial/eliminar/${nombreArchivo}`, { method: 'DELETE' }).then(res => res.json());
        
        if (respuesta.status === "ok") {
            alert("Mapa eliminado con éxito.");
            document.getElementById('visor').innerHTML = `<div class="contenido-visor">Selecciona un mapa para inspeccionar los datos</div>`;
            await cargarListaMapas();
        } else {
            alert("Error al eliminar el mapa.");
        }
    } catch (error) {
        console.error("Error:", error);
    }
};