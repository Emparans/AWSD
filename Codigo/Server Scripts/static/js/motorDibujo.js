// Variables internas del motor de renderizado
let scale, mapPositionX, mapPositionY, renderTileSize;

const tileSize = 48;
const playerScale = 1.5;
const poiScale = 1;
const sheetSize = 192;
const typeSheetSize = 32;
const typeSize = 16;
const typeScale = 1.5;

function obtenerTile(idTile) {
    /*
     * Obté les coordenades (x, y) dins del spritesheet d'un tile a partir del seu ID.
     * Assumeix un spritesheet quadrat de sheetSize x sheetSize, amb tiles quadrats de tileSize.
     * @param {number} idTile - Identificador del tile (0, 1, 2, ...)
     * @returns {Array} [x, y] posició dins del spritesheet en píxels
     */
    const columnas = sheetSize / tileSize; 
    return [(idTile * tileSize) % sheetSize, Math.floor(idTile / columnas) * tileSize];
}

function obtenerTipo(type) {
    /*
     * Obté les coordenades d'un tipus d'objecte (porta, clau) dins del seu spritesheet.
     * @param {number} type - Identificador del tipus (varia segons l'objecte)
     * @returns {Array} [x, y] posició dins del spritesheet de tipus
     */
    const columnas = typeSheetSize / typeSize; 
    return [(type * typeSize) % typeSheetSize, Math.floor(type / columnas) * typeSize];
}

function obtenerTamañoMapa(mapa) {
    /*
     * Calcula les dimensions reals del mapa (mínims i màxims en X i Y) a partir dels nodes explorats.
     * @param {Object} mapa - Objecte amb la propietat "nodes" (llista de caselles)
     * @returns {Object} { minX, maxX, minY, maxY, width, height }
     */
    const nodes = mapa.nodes;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(nodo => {
        if (nodo.coords[0] < minX) minX = nodo.coords[0];
        if (nodo.coords[0] > maxX) maxX = nodo.coords[0];
        if (nodo.coords[1] < minY) minY = nodo.coords[1];
        if (nodo.coords[1] > maxY) maxY = nodo.coords[1];
    });
    return { minX, maxX, minY, maxY, width: (maxX - minX + 1), height: (maxY - minY + 1) };
}

function dibujarTile(ctx, node, imagenes) {
    /*
     * Dibuixa una rajola (tile) al canvas, juntament amb els seus extres (objectes si en té).
     * @param {CanvasRenderingContext2D} ctx - Context del canvas
     * @param {Object} node - Node de la casella (conté coords, sprite, explored, typeTile, locked, id...)
     * @param {Object} imagenes - Objecte amb les imatges carregades (tileset, doors, keys, poi, player)
     */

    // Només es dibuixa si la casella ha estat explorada pel robot
    if(node.explored == false) return;

    let pos = node.coords;
    // Calcula la posició del tile al canvas tenint en compte el desplaçament (mapPosition)
    let x = (pos[0] * renderTileSize) + mapPositionX;
    let y = -(pos[1] * renderTileSize) + mapPositionY; // eix Y invertit (coordenades matemàtiques vs pantalla)

    // Obté la posició de la imatge al spritesheet
    let tileSource = obtenerTile(node.sprite);
    // Dibuixa la rajola
    ctx.drawImage(imagenes.tileset, tileSource[0], tileSource[1], tileSize, tileSize, x, y, renderTileSize, renderTileSize);

    // Dibuixa elements addicionals (claus, portes, QR) per sobre de la rajola
    dibujarExtra(ctx, node, [x, y], imagenes);
}

function dibujarExtra(ctx, node, pos, imagenes) {
    /*
     * Dibuixa els elements extra associats a una casella (clau, porta, QR).
     * @param {CanvasRenderingContext2D} ctx 
     * @param {Object} node 
     * @param {Array} pos - [x, y] posició superior esquerra de la rajola al canvas
     * @param {Object} imagenes 
     */

    // Mida final de l'objecte extra (escala base * escala global * typeScale)
    let renderTypeSize = 16 * scale * typeScale;
    let [x, y] = pos;
    // Centra l'objecte dins de la rajola
    x = x + (renderTileSize / 2) - (renderTypeSize / 2);
    y = y + (renderTileSize / 2) - (renderTypeSize / 2);

    // Cas especial: Punt d'interès (codi QR)
    if(node.typeTile === "?")
    {
        console.log(node.locked);
        // Nota: 'locked' s'usa per indicar si l'objecte encara està actiu (no agafat/resolt)
        if(!node.locked) {return; } // Si no està locked, no es dibuixa (ja ha estat interactuat)
        ctx.drawImage(imagenes.poi, x, y, renderTypeSize, renderTypeSize);
        return;
    }

    // Portes (D) o Claus (K)
    if (node.typeTile === "D" || node.typeTile === "K") {
        console.log(node.locked);
        if(!node.locked) {return; }
        let typeSource = obtenerTipo(node.id);
        let img = node.typeTile === "D" ? imagenes.doors : imagenes.keys;
        ctx.drawImage(img, typeSource[0], typeSource[1], typeSize, typeSize, x, y, renderTypeSize, renderTypeSize);
    }
}

function dibujarJugador(ctx, data, imagenes) {
    /*
     * Dibuixa el robot (jugador) a la seva posició actual, amb rotació segons la direcció.
     * @param {CanvasRenderingContext2D} ctx 
     * @param {Object} data - Conté l'estat del robot: robot.currentPos i robot.currentDir
     * @param {Object} imagenes 
     */

    // Calcula el centre de la casella on es troba el robot
    let centroX = (data.robot.currentPos[0] * renderTileSize) + mapPositionX + (renderTileSize / 2);
    let centroY = -(data.robot.currentPos[1] * renderTileSize) + mapPositionY + (renderTileSize / 2);
    let playerSize = 16 * scale * playerScale;
    let halfSize = playerSize / 2;
    
    // Mapeig de direccions a angles (en radians)
    let angulos = { "u": Math.PI, "l": Math.PI / 2, "d": 0, "r": (3 * Math.PI) / 2 };
    let angulo = angulos[data.robot.currentDir] || 0;

    // Dibuixa el jugador rotat
    ctx.save();
    ctx.translate(centroX, centroY);
    ctx.rotate(angulo);
    ctx.drawImage(imagenes.player, -halfSize, -halfSize, playerSize, playerSize);
    ctx.restore();
}

/*
function dibujarPOI(ctx, data, imagenes) {
    if (!data.pois) return;
    data.pois.forEach(nodo => {
        let x = (nodo.targetCoords[0] * renderTileSize) + mapPositionX + (renderTileSize / 2) - (16 * scale * poiScale / 2);
        let y = -(nodo.targetCoords[1] * renderTileSize) + mapPositionY + (renderTileSize / 2) - (16 * scale * poiScale / 2);
        let offset = 16 * scale;

        if (nodo.dirToLook === "d") y += offset;
        if (nodo.dirToLook === "u") y -= offset;
        if (nodo.dirToLook === "r") x += offset;
        if (nodo.dirToLook === "l") x -= offset;

    });
}
*/

export function dibujarTodoElMapa(canvas, ctx, data, imagenes) {
    /*
     * Funció principal que neteja el canvas, recalcula l'escala i les posicions,
     * i dibuixa tot el mapa (rajoles + extres + jugador).
     * @param {HTMLCanvasElement} canvas - Element canvas on dibuixar
     * @param {CanvasRenderingContext2D} ctx 
     * @param {Object} data - Dades completes del mapa (nodes, robot, etc.)
     * @param {Object} imagenes - Totes les imatges carregades (tileset, player, doors, keys, poi)
     */

    // Neteja el canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = false;

    // Calcula les dimensions reals del mapa
    const size = obtenerTamañoMapa(data);
    // Calcula l'escala perquè el mapa entri dins del canvas (80% de l'amplada)
    let q = (canvas.width / tileSize) * 0.8;
    scale = q / Math.max(size.width, size.height);
    renderTileSize = scale * tileSize;

    // Calcula el desplaçament per centrar el mapa al canvas
    mapPositionX = (canvas.width / 2) - ((size.width * renderTileSize) / 2) - (size.minX * renderTileSize);
    mapPositionY = (canvas.height / 2) - ((size.height * renderTileSize) / 2) + (size.maxY * renderTileSize);
    
    // Dibuixa totes les rajoles (només les explorades)
    data.nodes.forEach(nodo => dibujarTile(ctx, nodo, imagenes));
    // Dibuixa el jugador al damunt
    dibujarJugador(ctx, data, imagenes);
    //dibujarPOI(ctx, data, imagenes);
}