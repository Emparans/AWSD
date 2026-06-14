// Importa el motor de dibuix del mapa
import { dibujarTodoElMapa } from './motorDibujo.js';

const imagenes = {
    tileset: new Image(),
    player: new Image(),
    doors: new Image(),
    keys: new Image(),
    poi: new Image()
};

function cargarImagen(img, src) {
    /*
    * Càrrega una imatge i retorna una Promise que es resol quan la imatge està a punt.
    * @param {HTMLImageElement} img - Objecte Image a carregar
    * @param {string} src - Ruta de la imatge
    * @returns {Promise<HTMLImageElement>}
    */    
    return new Promise(resolve => {
        img.onload = () => resolve(img);
        img.src = src;
    });
}

async function cargarListaMapas() {
    /*
     * Obté la llista de mapes des del backend i genera els botons de selecció.
     * Actualitza el contingut del <div id="lista">.
     */
    const lista = document.getElementById('lista');
    // Crida a l'API per obtenir els noms dels fitxers JSON del bucket
    const respuesta = await fetch('/historial/obtenerMapas').then(res => res.json());
    
    // Per cada nom de mapa, crea un botó amb l'esdeveniment onclick personalitzat
    lista.innerHTML = respuesta.mapas.map(m => `
        <button class="btn-mapa-modular" onclick="verMapa('${m}')">
            ${m.replace('.json','').toUpperCase()}
        </button>
    `).join('');
}

// Quan el DOM estigui completament carregat, s'inicien les càrregues de recursos
window.addEventListener('DOMContentLoaded', async () => {
    const cargaRecursos = Promise.all([
        cargarImagen(imagenes.player, "/static/sprites/player.png"),
        cargarImagen(imagenes.tileset, '/static/sprites/tileset.png'),
        cargarImagen(imagenes.doors, "/static/sprites/doors.png"),
        cargarImagen(imagenes.poi, "/static/sprites/poi.png"),
        cargarImagen(imagenes.keys, "/static/sprites/keys.png")
    ]);

    // Carrega la llista de mapes i després les imatges
    await cargarListaMapas();
    await cargaRecursos;
});

window.verMapa = async function(nombreArchivo) {
    /*
     * Funció global (disponible a l'HTML) per visualitzar un mapa seleccionat.
     * Rep el nom de l'arxiu (ex: "mapa1.json"), descarrega el contingut i el dibuixa.
     */
    const visor = document.getElementById('visor');
    visor.innerHTML = "<div class='contenido-visor'>Cargando datos de GCS...</div>";

    // Obté les dades del mapa des del backend (cloud storage)
    const data = await fetch(`/historial/obtenerMapa/${nombreArchivo}`).then(res => res.json());

    if (data) {
        // Extreu les metadades de l'apartat "state" del JSON
        const creador = data.state.creador || "usuario"
        const tiempo = data.state.tiempo || "00:00";
        const puntos = data.state.score || 0;
        const fecha = data.state.fecha || "FECHA"
        const nombreMapa = nombreArchivo.replace('.json', '').toUpperCase();
        const fecha_split = fecha.split(" ")
        const dia = fecha_split[0]
        let hora = fecha_split[3]
        if (hora == undefined) hora = "";

        // Construeix el panell lateral d'informació + el canvas
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
                        <div class="info-value highlight-blue">${creador}</div>
                    </div>

                    <div class="sub-panel-info">
                        <div class="info-header">Fecha</div>
                        <div class="info-value highlight-blue">${dia} ${hora}</div>
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

        // Obté el canvas acabat de crear i el seu context
        const nuevoCanvas = document.getElementById('juego');
        const ctx = nuevoCanvas.getContext('2d');
        // Dibuixa tot el mapa utilitzant el mòdul extern, passant-li les dades i les imatges
        dibujarTodoElMapa(nuevoCanvas, ctx, data, imagenes);
    }
};

window.abrirPopUpEliminar = function(nombreArchivo) {
    /*
     * Mostra el pop-up de confirmació per eliminar un mapa.
     * Desa el nom de l'arxiu en un camp ocult i fa visible la capa de fons.
     */
    document.getElementById('archivoAEliminar').value = nombreArchivo;
    document.getElementById('capaFondoEliminar').style.display = 'flex'; // El único cambio de estilo permitido por JS para mostrar el pop-up
};

window.cerrarPopUpEliminar = function() {
    /*
     * Tanca el pop-up d'eliminació.
     */
    document.getElementById('capaFondoEliminar').style.display = 'none';
};

window.confirmarEliminarDatos = async function() {
    /*
     * Confirma l'eliminació del mapa: crida amb el mètode DELETE i, si té èxit,
     * recarrega la llista de mapes i neteja el visor.
     */
    const nombreArchivo = document.getElementById('archivoAEliminar').value;
    cerrarPopUpEliminar();

    try {
        const respuesta = await fetch(`/historial/eliminar/${nombreArchivo}`, { method: 'DELETE' }).then(res => res.json());
        
        if (respuesta.status === "ok") {
            alert("Mapa eliminado con éxito.");
            // Neteja l'àrea de visualització
            document.getElementById('visor').innerHTML = `<div class="contenido-visor">Selecciona un mapa para inspeccionar los datos</div>`;
            // Recarrega la llista de mapes (actualitza els botons)
            await cargarListaMapas();
        } else {
            alert("Error al eliminar el mapa.");
        }
    } catch (error) {
        console.error("Error:", error);
    }
};