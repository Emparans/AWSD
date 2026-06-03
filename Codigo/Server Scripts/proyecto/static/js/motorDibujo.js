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
    const columnas = sheetSize / tileSize; 
    return [(idTile * tileSize) % sheetSize, Math.floor(idTile / columnas) * tileSize];
}

function obtenerTipo(type) {
    const columnas = typeSheetSize / typeSize; 
    return [(type * typeSize) % typeSheetSize, Math.floor(type / columnas) * typeSize];
}

function obtenerTamañoMapa(mapa) {
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
    if(node.explored == false) return;

    let pos = node.coords;
    let x = (pos[0] * renderTileSize) + mapPositionX;
    let y = -(pos[1] * renderTileSize) + mapPositionY;

    let tileSource = obtenerTile(node.sprite);
    ctx.drawImage(imagenes.tileset, tileSource[0], tileSource[1], tileSize, tileSize, x, y, renderTileSize, renderTileSize);

    dibujarExtra(ctx, node, [x, y], imagenes);
}

function dibujarExtra(ctx, node, pos, imagenes) {
    let renderTypeSize = 16 * scale * typeScale;
    let [x, y] = pos;
    x = x + (renderTileSize / 2) - (renderTypeSize / 2);
    y = y + (renderTileSize / 2) - (renderTypeSize / 2);


    if(node.typeTile === "?")
    {
        console.log(node.locked);
        if(!node.locked) {return; }
        ctx.drawImage(imagenes.poi, x, y, renderTypeSize, renderTypeSize);
        return;
    }

    if (node.typeTile === "D" || node.typeTile === "K") {
        console.log(node.locked);
        if(!node.locked) {return; }
        let typeSource = obtenerTipo(node.id);
        let img = node.typeTile === "D" ? imagenes.doors : imagenes.keys;
        ctx.drawImage(img, typeSource[0], typeSource[1], typeSize, typeSize, x, y, renderTypeSize, renderTypeSize);
    }
}

function dibujarJugador(ctx, data, imagenes) {
    let centroX = (data.robot.currentPos[0] * renderTileSize) + mapPositionX + (renderTileSize / 2);
    let centroY = -(data.robot.currentPos[1] * renderTileSize) + mapPositionY + (renderTileSize / 2);
    let playerSize = 16 * scale * playerScale;
    let halfSize = playerSize / 2;
    
    let angulos = { "u": Math.PI, "l": Math.PI / 2, "d": 0, "r": (3 * Math.PI) / 2 };
    let angulo = angulos[data.robot.currentDir] || 0;

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
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.imageSmoothingEnabled = false;

    const size = obtenerTamañoMapa(data);
    let q = (canvas.width / tileSize) * 0.8;
    scale = q / Math.max(size.width, size.height);
    renderTileSize = scale * tileSize;

    mapPositionX = (canvas.width / 2) - ((size.width * renderTileSize) / 2) - (size.minX * renderTileSize);
    mapPositionY = (canvas.height / 2) - ((size.height * renderTileSize) / 2) + (size.maxY * renderTileSize);
    
    data.nodes.forEach(nodo => dibujarTile(ctx, nodo, imagenes));
    dibujarJugador(ctx, data, imagenes);
    //dibujarPOI(ctx, data, imagenes);
}