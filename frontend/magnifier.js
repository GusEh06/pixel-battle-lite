/* ===================================
   MAGNIFIER.JS - Sistema de Lupa
   =================================== */


// Configuración de la lupa
const MAGNIFIER_RADIUS = 85;
const MAGNIFIER_ZOOM = 2;
const MAGNIFIER_BORDER_WIDTH = 0;
const MAGNIFIER_BORDER_COLOR = '#667eea';

// 🔧 FIX: Referencias al DOM (redefinir aquí)
const mainCanvas = document.getElementById('pixel-canvas');
const magnifierCanvas = document.getElementById('magnifier-canvas');
const magnifierCtx = magnifierCanvas.getContext('2d');

// 🔧 FIX: También necesitamos acceso al contexto del canvas principal
const mainCtx = mainCanvas.getContext('2d');


// Estado de la lupa
let magnifierActive = false;
let magnifierX = 0;
let magnifierY = 0;

/* ===================================
   CONFIGURACIÓN INICIAL
   =================================== */

/**
 * Configura el tamaño del canvas de la lupa
 */

// 🔍 TEST: Verificar que los eventos de teclado funcionen
console.log('🔍 Magnifier.js cargado');

document.addEventListener('keydown', (event) => {
    console.log('⌨️ Tecla presionada:', event.key);
});

/**
 * Configura el tamaño del canvas de la lupa
 */
function setupMagnifierCanvas() {
    magnifierCanvas.width = mainCanvas.width;
    magnifierCanvas.height = mainCanvas.height;

    console.log('🔍 Lupa configurada');
    console.log('   Canvas principal:', mainCanvas.width, 'x', mainCanvas.height);
    console.log('   Canvas lupa:', magnifierCanvas.width, 'x', magnifierCanvas.height);
}

/* ===================================
   EVENT LISTENERS
   =================================== */

/**
 * Detectar cuando se presiona la tecla Z
 */
document.addEventListener('keydown', (event) => {
    if (event.key === 'z' || event.key === 'Z') {
        console.log('⌨️ Tecla Z presionada');
        if (!magnifierActive) {
            activateMagnifier();
        }
    }
});

/**
 * Detectar cuando se suelta la tecla Z
 */
document.addEventListener('keyup', (event) => {
    if (event.key === 'z' || event.key === 'Z') {
        console.log('⌨️ Tecla Z soltada');
        if (magnifierActive) {
            deactivateMagnifier();
        }
    }
});

/**
 * Seguir el movimiento del mouse cuando la lupa está activa
 */
mainCanvas.addEventListener('mousemove', (event) => {
    console.log('🖱️ Mouse move detectado, lupa activa:', magnifierActive);

    if (magnifierActive) {
        updateMagnifierPosition(event);
        drawMagnifier();
    }
});

/**
 * Ocultar lupa cuando el mouse sale del canvas
 */
mainCanvas.addEventListener('mouseleave', () => {
    console.log('🖱️ Mouse salió del canvas');
    if (magnifierActive) {
        hideMagnifier();
    }
});

/**
 * Mostrar lupa de nuevo cuando el mouse vuelve al canvas
 */
mainCanvas.addEventListener('mouseenter', (event) => {
    console.log('🖱️ Mouse entró al canvas');
    if (magnifierActive) {
        updateMagnifierPosition(event);
        drawMagnifier();
    }
});

/* ===================================
   FUNCIONES DE ACTIVACIÓN/DESACTIVACIÓN
   =================================== */

/**
 * Activa la lupa
 */
function activateMagnifier() {
    magnifierActive = true;
    magnifierCanvas.classList.add('active');
    mainCanvas.style.cursor = 'none';  // Ocultar cursor normal

    console.log('🔍 Lupa activada');
    console.log('   Canvas display:', window.getComputedStyle(magnifierCanvas).display);
}

/**
 * Desactiva la lupa
 */
function deactivateMagnifier() {
    magnifierActive = false;
    magnifierCanvas.classList.remove('active');
    mainCanvas.style.cursor = 'crosshair';  // Restaurar cursor
    hideMagnifier();

    console.log('🔍 Lupa desactivada');
}

/**
 * Oculta visualmente la lupa (limpia el canvas)
 */
function hideMagnifier() {
    magnifierCtx.clearRect(0, 0, magnifierCanvas.width, magnifierCanvas.height);
}

/* ===================================
   ACTUALIZACIÓN DE POSICIÓN
   =================================== */

/**
 * Actualiza la posición de la lupa según el mouse
 */
function updateMagnifierPosition(event) {
    const rect = mainCanvas.getBoundingClientRect();

    magnifierX = event.clientX - rect.left;
    magnifierY = event.clientY - rect.top;

    console.log('🔍 Posición actualizada:', magnifierX.toFixed(0), magnifierY.toFixed(0));
}

/* ===================================
   DIBUJO DE LA LUPA
   =================================== */

/**
 * Dibuja la lupa circular con zoom
 */
function drawMagnifier() {
    // 🔧 Mantener nitidez
    magnifierCtx.imageSmoothingEnabled = false;

    // Limpiar canvas anterior
    magnifierCtx.clearRect(0, 0, magnifierCanvas.width, magnifierCanvas.height);

    if (magnifierX < 0 || magnifierY < 0 ||
        magnifierX > CANVAS_SIZE || magnifierY > CANVAS_SIZE) {
        return;
    }

    magnifierCtx.save();

    // 1. MÁSCARA CIRCULAR
    magnifierCtx.beginPath();
    magnifierCtx.arc(magnifierX, magnifierY, MAGNIFIER_RADIUS, 0, Math.PI * 2);
    magnifierCtx.clip();

    // 2. FONDO BLANCO
    magnifierCtx.fillStyle = '#FFFFFF';
    magnifierCtx.fillRect(
        magnifierX - MAGNIFIER_RADIUS,
        magnifierY - MAGNIFIER_RADIUS,
        MAGNIFIER_RADIUS * 2,
        MAGNIFIER_RADIUS * 2
    );

    // 3. DIBUJAR LÍNEAS DEL CANVAS REAL (Zoom del grid #EEEEEE)
    const sourceSize = (MAGNIFIER_RADIUS * 2) / MAGNIFIER_ZOOM;
    const startX = Math.floor((magnifierX - sourceSize / 2) / PIXEL_SIZE);
    const startY = Math.floor((magnifierY - sourceSize / 2) / PIXEL_SIZE);
    const endX = Math.ceil((magnifierX + sourceSize / 2) / PIXEL_SIZE);
    const endY = Math.ceil((magnifierY + sourceSize / 2) / PIXEL_SIZE);

    magnifierCtx.strokeStyle = '#EEEEEE'; // Mismo color que el canvas real
    magnifierCtx.lineWidth = 1;

    for (let x = startX; x <= endX; x++) {
        for (let y = startY; y <= endY; y++) {
            // Posición con zoom
            const posX = magnifierX + (x * PIXEL_SIZE - magnifierX) * MAGNIFIER_ZOOM;
            const posY = magnifierY + (y * PIXEL_SIZE - magnifierY) * MAGNIFIER_ZOOM;
            const size = PIXEL_SIZE * MAGNIFIER_ZOOM;

            // Dibujar el recuadro del grid
            magnifierCtx.strokeRect(posX, posY, size, size);

            // 4. DIBUJAR EL PÍXEL SI ESTÁ PINTADO
            const key = `${x},${y}`;
            const color = canvasState[key];
            if (color) {
                magnifierCtx.fillStyle = color;
                magnifierCtx.fillRect(posX, posY, size, size);
                // Volver a dibujar el borde sobre el color para que se vea igual que en el canvas
                magnifierCtx.strokeRect(posX, posY, size, size);
            }
        }
    }

    // 5. CRUZ DE REFERENCIA
    drawCrosshair();

    magnifierCtx.restore();

    // 6. BORDE DE LA LUPA
    drawMagnifierBorder();
}

/**
 * Dibuja el grid ampliado dentro de la lupa
 */
function drawMagnifiedGrid() {
    // Función desactivada: ya no dibujamos el grid para mantener la lupa limpia y nítida
}

/**
 * Dibuja una cruz en el centro de la lupa (punto de referencia)
 */
function drawCrosshair() {
    const crosshairSize = 10;

    magnifierCtx.strokeStyle = 'rgba(255, 0, 0, 0.8)';
    magnifierCtx.lineWidth = 2;

    // Línea horizontal
    magnifierCtx.beginPath();
    magnifierCtx.moveTo(magnifierX - crosshairSize, magnifierY);
    magnifierCtx.lineTo(magnifierX + crosshairSize, magnifierY);
    magnifierCtx.stroke();

    // Línea vertical
    magnifierCtx.beginPath();
    magnifierCtx.moveTo(magnifierX, magnifierY - crosshairSize);
    magnifierCtx.lineTo(magnifierX, magnifierY + crosshairSize);
    magnifierCtx.stroke();
}

/**
 * Dibuja el borde circular de la lupa
 */
function drawMagnifierBorder() {
    magnifierCtx.strokeStyle = MAGNIFIER_BORDER_COLOR;
    magnifierCtx.lineWidth = MAGNIFIER_BORDER_WIDTH;
    magnifierCtx.shadowColor = 'rgba(0, 0, 0, 0.3)';
    magnifierCtx.shadowBlur = 10;

    magnifierCtx.beginPath();
    magnifierCtx.arc(magnifierX, magnifierY, MAGNIFIER_RADIUS, 0, Math.PI * 2);
    magnifierCtx.stroke();

    // Quitar sombra para no afectar otros dibujos
    magnifierCtx.shadowColor = 'transparent';
    magnifierCtx.shadowBlur = 0;
}

/* ===================================
   INICIALIZACIÓN
   =================================== */

// Configurar la lupa cuando cargue el script
setupMagnifierCanvas();