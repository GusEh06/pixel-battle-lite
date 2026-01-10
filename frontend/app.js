/* ===================================
   APP.JS - Lógica Principal del Canvas
   =================================== */

// Configuración del canvas
const GRID_SIZE = 32;           // Tamaño del grid (32x32 píxeles)
const PIXEL_SIZE = 20;          // Cada píxel lógico ocupa 20x20 px reales
const CANVAS_SIZE = GRID_SIZE * PIXEL_SIZE;  // 640x640 px

// Referencias a elementos del DOM
const canvas = document.getElementById('pixel-canvas');
const ctx = canvas.getContext('2d');
const colorPicker = document.getElementById('color-picker');
const colorDisplay = document.getElementById('color-display');
const cooldownTimer = document.getElementById('cooldown-timer');
const totalPixelsElement = document.getElementById('total-pixels');
const userPixelsElement = document.getElementById('user-pixels');
const pixelInfoElement = document.getElementById('pixel-info');
const recentActivityElement = document.getElementById('recent-activity');

// Estado de la aplicación
let selectedColor = '#FF6B6B';  // Color seleccionado actualmente
let canPaint = true;             // ¿Usuario puede pintar? (cooldown)
let cooldownEndTime = null;      // Timestamp de cuándo termina el cooldown
let userId = 'anonymous_user';   // ID del usuario (por ahora estático)
let canvasState = {};            // Estado actual del canvas {`x,y`: color}

/* ===================================
   INICIALIZACIÓN
   =================================== */

/**
 * Función que se ejecuta cuando carga la página
 */
async function init() {
    console.log('🎨 Iniciando Pixel Canvas Lite...');

    // 🔧 FIX: Sincronizar color inicial desde el HTML
    selectedColor = colorPicker.value.toUpperCase();
    colorDisplay.textContent = selectedColor;
    console.log('🎨 Color inicial:', selectedColor);

    // 1. Dibujar el grid vacío
    drawEmptyGrid();

    // 2. Cargar el estado actual del canvas desde el backend
    await loadCanvasState();

    // 3. Cargar estadísticas generales
    await updateStats();

    // 4. Configurar event listeners
    setupEventListeners();

    // 5. Iniciar loop de actualización
    startUpdateLoop();

    console.log('✅ Canvas inicializado correctamente');
}

/* ===================================
   DIBUJO DEL CANVAS
   =================================== */

/**
 * Dibuja el grid vacío con líneas de separación
 */
function drawEmptyGrid() {
    // Fondo blanco
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // Dibujar líneas del grid
    ctx.strokeStyle = '#EEEEEE';
    ctx.lineWidth = 1;

    // Líneas verticales
    for (let x = 0; x <= GRID_SIZE; x++) {
        ctx.beginPath();
        ctx.moveTo(x * PIXEL_SIZE, 0);
        ctx.lineTo(x * PIXEL_SIZE, CANVAS_SIZE);
        ctx.stroke();
    }

    // Líneas horizontales
    for (let y = 0; y <= GRID_SIZE; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * PIXEL_SIZE);
        ctx.lineTo(CANVAS_SIZE, y * PIXEL_SIZE);
        ctx.stroke();
    }
}

/**
 * Dibuja un píxel individual en el canvas
 * @param {number} x - Coordenada X lógica (0-31)
 * @param {number} y - Coordenada Y lógica (0-31)
 * @param {string} color - Color en formato #RRGGBB
 */
function drawPixel(x, y, color) {
    console.log(`🖌️ drawPixel llamado: (${x}, ${y}) color: ${color}`);

    const realX = x * PIXEL_SIZE;
    const realY = y * PIXEL_SIZE;

    ctx.fillStyle = color;
    ctx.fillRect(realX, realY, PIXEL_SIZE, PIXEL_SIZE);

    ctx.strokeStyle = '#EEEEEE';
    ctx.strokeRect(realX, realY, PIXEL_SIZE, PIXEL_SIZE);
}

/**
 * Redibuja todo el canvas con el estado actual
 */
function redrawCanvas() {
    drawEmptyGrid();

    // Dibujar cada píxel guardado en el estado
    for (const [coords, color] of Object.entries(canvasState)) {
        const [x, y] = coords.split(',').map(Number);
        drawPixel(x, y, color);
    }
}

/* ===================================
   CARGA DE DATOS DEL BACKEND
   =================================== */

/**
 * Carga el estado completo del canvas desde el backend
 */
async function loadCanvasState() {
    try {
        const data = await getCanvasState();

        // Convertir array de píxeles a objeto {`x,y`: color}
        canvasState = {};
        data.pixels.forEach(pixel => {
            const key = `${pixel.x},${pixel.y}`;
            canvasState[key] = pixel.color;
        });

        // Redibujar el canvas con los datos
        redrawCanvas();

        console.log(`📊 Canvas cargado: ${Object.keys(canvasState).length} píxeles`);

    } catch (error) {
        console.error('❌ Error al cargar canvas:', error);
        alert('Error al cargar el canvas. ¿El backend está corriendo?');
    }
}

/**
 * Actualiza las estadísticas mostradas en la UI
 */
async function updateStats() {
    try {
        // Obtener info general del canvas
        const canvasInfo = await getCanvasInfo();
        totalPixelsElement.textContent = canvasInfo.total_pixels_placed;

        // Obtener stats del usuario
        const userStats = await getUserStats(userId);
        userPixelsElement.textContent = userStats.total_pixels_placed;

        // Verificar si hay cooldown activo
        if (userStats.can_paint === false && userStats.cooldown_remaining > 0) {
            startCooldown(userStats.cooldown_remaining);
        }

    } catch (error) {
        console.error('❌ Error al actualizar stats:', error);
    }
}

/* ===================================
   INTERACCIÓN DEL USUARIO
   =================================== */

/**
 * Configura todos los event listeners
 */
function setupEventListeners() {
    // Click en el canvas para pintar
    canvas.addEventListener('click', handleCanvasClick);

    // Hover en el canvas para mostrar info del píxel
    canvas.addEventListener('mousemove', handleCanvasHover);

    // 🔧 FIX: Escuchar AMBOS eventos (input Y change)
    colorPicker.addEventListener('input', handleColorChange);
    colorPicker.addEventListener('change', handleColorChange);
}

/**
 * Maneja el hover sobre el canvas para mostrar info
 */
function handleCanvasHover(event) {
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    const x = Math.floor(mouseX / PIXEL_SIZE);
    const y = Math.floor(mouseY / PIXEL_SIZE);

    // Validar coordenadas
    if (x < 0 || x >= GRID_SIZE || y < 0 || y >= GRID_SIZE) {
        return;
    }

    // Obtener info del píxel del estado local
    const key = `${x},${y}`;
    const color = canvasState[key];

    if (color) {
        pixelInfoElement.innerHTML = `
            <p><strong>Posición:</strong> (${x}, ${y})</p>
            <p><strong>Color:</strong> ${color}</p>
            <p style="background: ${color}; width: 40px; height: 40px; border: 2px solid #ccc; margin-top: 5px; border-radius: 4px;"></p>
        `;
    } else {
        pixelInfoElement.innerHTML = `
            <p><strong>Posición:</strong> (${x}, ${y})</p>
            <p><em>Sin pintar</em></p>
        `;
    }
}

/**
 * Maneja el click en el canvas
 */
async function handleCanvasClick(event) {
    // Verificar si puede pintar (cooldown)
    if (!canPaint) {
        alert('⏱️ Debes esperar el cooldown');
        return;
    }

    // Obtener coordenadas del click
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    // Convertir a coordenadas lógicas
    const x = Math.floor(mouseX / PIXEL_SIZE);
    const y = Math.floor(mouseY / PIXEL_SIZE);

    // Validar que esté dentro del grid
    if (x < 0 || x >= GRID_SIZE || y < 0 || y >= GRID_SIZE) {
        return;
    }

    // 🔧 FIX: Leer el color directamente del picker para estar seguros
    const colorToUse = colorPicker.value.toUpperCase();

    console.log(`🖱️ Click en (${x}, ${y}) con color ${colorToUse}`);

    // Intentar pintar el píxel
    try {
        const response = await paintPixel(x, y, colorToUse, userId);

        console.log('📦 Respuesta completa del backend:', JSON.stringify(response, null, 2));

        // 🔧 Validar que la respuesta tenga la estructura esperada
        if (!response || !response.pixel) {
            console.error('❌ Respuesta inválida del backend:', response);
            alert('Error: Respuesta inválida del servidor');
            return;
        }

        const pixelData = response.pixel;
        const finalColor = pixelData.color;

        console.log('✅ Color extraído:', finalColor);

        // Actualizar el estado local
        const key = `${x},${y}`;
        canvasState[key] = finalColor;

        // Dibujar el píxel
        console.log('🖌️ Dibujando con color:', finalColor);
        drawPixel(x, y, finalColor);

        // Iniciar cooldown
        const cooldownSeconds = response.cooldown_remaining || 30;
        startCooldown(cooldownSeconds);

        // Actualizar estadísticas
        await updateStats();

        console.log('✅ Píxel pintado exitosamente');

    } catch (error) {
        console.error('❌ Error al pintar píxel:', error);

        // Mejorar el mensaje de error
        const errorMessage = error.message || 'Error desconocido';

        if (errorMessage.includes('cooldown') || errorMessage.includes('429')) {
            alert('⏱️ Debes esperar el cooldown antes de pintar');
        } else if (errorMessage.includes('petición')) {
            alert('❌ Error de conexión con el servidor. Verifica que el backend esté corriendo.');
        } else {
            alert('Error: ' + errorMessage);
        }
    }
}

/**
 * Maneja el cambio de color en el picker
 */
function handleColorChange(event) {
    selectedColor = event.target.value.toUpperCase();
    colorDisplay.textContent = selectedColor;

    // 🔍 DEBUG: Ver que se está ejecutando
    console.log('🎨 Color cambiado a:', selectedColor);
    console.log('   Event type:', event.type);
}

/* ===================================
   SISTEMA DE COOLDOWN
   =================================== */

/**
 * Inicia el cooldown después de pintar
 * @param {number} seconds - Segundos de cooldown
 */
function startCooldown(seconds) {
    canPaint = false;
    cooldownEndTime = Date.now() + (seconds * 1000);

    // Cambiar estilos del timer
    cooldownTimer.classList.remove('cooldown-ready');
    cooldownTimer.classList.add('cooldown-active');

    updateCooldownDisplay();
}

/**
 * Actualiza el display del cooldown cada segundo
 */
function updateCooldownDisplay() {
    if (!cooldownEndTime) {
        return;
    }

    const now = Date.now();
    const remaining = Math.max(0, Math.ceil((cooldownEndTime - now) / 1000));

    if (remaining > 0) {
        cooldownTimer.textContent = `${remaining}s`;
        setTimeout(updateCooldownDisplay, 1000);  // Actualizar en 1 segundo
    } else {
        // Cooldown terminado
        canPaint = true;
        cooldownEndTime = null;
        cooldownTimer.textContent = 'Listo';
        cooldownTimer.classList.remove('cooldown-active');
        cooldownTimer.classList.add('cooldown-ready');
    }
}

/* ===================================
   ACTIVIDAD RECIENTE
   =================================== */

/**
 * Actualiza la lista de actividad reciente
 */
async function updateRecentActivity() {
    try {
        const recentPixels = await getRecentPixels(5);  // Últimos 5 píxeles

        if (recentPixels.length === 0) {
            recentActivityElement.innerHTML = '<p class="empty-state">Sin actividad aún</p>';
            return;
        }

        // Generar HTML de la lista
        const activityHTML = recentPixels.map(pixel => {
            const timeAgo = getTimeAgo(pixel.created_at);
            return `
                <div class="activity-item">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 20px; height: 20px; background: ${pixel.color}; border: 1px solid #ccc; border-radius: 3px;"></div>
                        <div>
                            <strong>(${pixel.x}, ${pixel.y})</strong>
                            <br>
                            <small>${timeAgo}</small>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        recentActivityElement.innerHTML = activityHTML;

    } catch (error) {
        console.error('❌ Error al actualizar actividad:', error);
    }
}

/**
 * Convierte un timestamp a formato "hace X tiempo"
 * @param {string} timestamp - ISO timestamp
 * @returns {string} - Texto formateado
 */
function getTimeAgo(timestamp) {
    const now = new Date();
    const past = new Date(timestamp);
    const diffSeconds = Math.floor((now - past) / 1000);

    if (diffSeconds < 60) return 'hace unos segundos';
    if (diffSeconds < 3600) return `hace ${Math.floor(diffSeconds / 60)} min`;
    if (diffSeconds < 86400) return `hace ${Math.floor(diffSeconds / 3600)} horas`;
    return `hace ${Math.floor(diffSeconds / 86400)} días`;
}

/* ===================================
   LOOP DE ACTUALIZACIÓN
   =================================== */

/**
 * Inicia un loop que actualiza datos periódicamente
 */
function startUpdateLoop() {
    // Actualizar actividad reciente cada 10 segundos
    updateRecentActivity();
    setInterval(updateRecentActivity, 10000);

    // Actualizar estadísticas cada 30 segundos
    setInterval(updateStats, 30000);
}

/* ===================================
   EJECUCIÓN AL CARGAR LA PÁGINA
   =================================== */

// Ejecutar init cuando el DOM esté completamente cargado
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();  // DOM ya está listo
}