let chunks = [], recorder;


const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const wsUri = `${protocol}${window.location.host}/control/client`;
const socket = new WebSocket(wsUri);

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.pregunta) {
        mostrarPregunta(data.pregunta);
    }
};

/*
async function mandarQR() {
    const res = await fetch("/control/leer-qr", { method: "POST" });
    const data = await res.json();
    mostrarPregunta(data.pregunta);
}*/

function mostrarPregunta(pregunta) {
    // Estructura limpia garantizada por el nuevo CSS
    document.getElementById("contenedor_pregunta").innerHTML = `
        <h3>${pregunta}</h3>
        
        <div style="display: flex; gap: 15px;">
            <button class="btn" onclick="toggleGrabacion(this)">Grabar</button>
            <button class="btn" id="btn-send" onclick="enviarAudio(this)" disabled>Enviar</button>
        </div>

        <div id="respuesta-vm" style="width: 100%;"></div>
    `;
}

async function toggleGrabacion(btn) {
    if (!recorder || recorder.state === "inactive") {
        chunks = [];
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream);
        recorder.ondataavailable = e => chunks.push(e.data);
        recorder.onstop = () => document.getElementById("btn-send").disabled = false;
        
        recorder.start();
        btn.innerText = "Parar";
    } else {
        recorder.stop();
        btn.innerText = "Grabar";
    }
}

async function enviarAudio(btn) {
    btn.disabled = true;
    try {
        const res = await fetch("/control/procesar-audio", {
            method: "POST",
            body: new Blob(chunks, { type: 'audio/wav' })
        });

        const data = await res.json();

        if (data && data.texto) {
        document.getElementById("respuesta-vm").innerText = data.texto; 
        
        if (data.audio) {
            const audioUrl = `data:audio/wav;base64,${data.audio}`;
            const audio = new Audio(audioUrl);
            audio.play();
        }
        } else {
            console.error("El servidor no devolvió el formato esperado:", data);
        }

    } catch (err) {
        console.error("Error:", err);
        btn.disabled = false; 
    }
}