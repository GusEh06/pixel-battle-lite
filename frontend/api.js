/* ===================================
   API.JS - Comunicación con Backend
   =================================== */

// URL base del backend (cambiar si usas otro puerto/host)
const API_BASE_URL = 'http://127.0.0.1:8000/api';

/* ===================================
   FUNCIONES AUXILIARES
   =================================== */

/**
 * Función genérica para hacer peticiones HTTP
 * @param {string} endpoint - Ruta del endpoint (ej: '/pixels')
 * @param {object} options - Opciones de fetch (method, body, etc.)
 * @returns {Promise} - Respuesta parseada como JSON
 */

async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        // Si la respuesta no es OK (status 200-299), lanzar error
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error en la petición');
        }

        return await response.json();
    } catch (error) {
        console.error('Error en API:', error);
        throw error;  // Re-lanzar para que quien llame pueda manejarlo
    }
}

/* ===================================
   ENDPOINTS ESPECÍFICOS
   =================================== */

/**
 * Pintar un píxel en el canvas
 * @param {number} x - Coordenada X (0-31)
 * @param {number} y - Coordenada Y (0-31)
 * @param {string} color - Color en formato #RRGGBB
 * @param {string} userId - ID del usuario (por ahora 'anonymous_user')
 * @returns {Promise<object>} - Datos del píxel creado
 */
async function paintPixel(x, y, color, userId = 'anonymous_user') {
    return await apiRequest('/pixels', {
        method: 'POST',
        body: JSON.stringify({
            x: x,
            y: y,
            color: color,
            user_id: userId
        })
    });
}

/**
 * Obtener el estado completo del canvas (todos los píxeles)
 * @returns {Promise<object>} - Objeto con el estado del canvas
 */
async function getCanvasState() {
    return await apiRequest('/canvas/state');
}

/**
 * Obtener información de un píxel específico
 * @param {number} x - Coordenada X
 * @param {number} y - Coordenada Y
 * @returns {Promise<object>} - Info del píxel (color, último usuario, etc.)
 */
async function getPixelInfo(x, y) {
    return await apiRequest(`/canvas/pixel/${x}/${y}`);
}

/**
 * Obtener el historial completo de un píxel
 * @param {number} x - Coordenada X
 * @param {number} y - Coordenada Y
 * @returns {Promise<array>} - Array de eventos históricos
 */
async function getPixelHistory(x, y) {
    return await apiRequest(`/pixels/history/${x}/${y}`);
}

/**
 * Obtener píxeles pintados recientemente
 * @param {number} limit - Cantidad de píxeles a traer (default: 10)
 * @returns {Promise<array>} - Array de píxeles recientes
 */
async function getRecentPixels(limit = 10) {
    return await apiRequest(`/pixels/recent?limit=${limit}`);
}

/**
 * Obtener información general del canvas
 * @returns {Promise<object>} - Estadísticas generales (total píxeles, etc.)
 */
async function getCanvasInfo() {
    return await apiRequest('/canvas/info');
}

/**
 * Obtener estadísticas de un usuario
 * @param {string} userId - ID del usuario
 * @returns {Promise<object>} - Stats del usuario (total pintados, último píxel, etc.)
 */
async function getUserStats(userId = 'anonymous_user') {
    return await apiRequest(`/users/${userId}/stats`);
}

/**
 * Verificar la salud del backend
 * @returns {Promise<object>} - Estado de la API y la base de datos
 */
async function checkHealth() {
    return await apiRequest('/health');
}