/* ============================================================
 * File      : config.js
 * Proyek    : {{project_name}}
 * Deskripsi : Sumber data situs. Satu-satunya tempat untuk berpindah
 *             dari data contoh (mock) ke API sungguhan (live).
 * Dibuat    : sistem skill website {{version}}, {{date}}
 * ============================================================ */

// ============================================================
// ======================== SUMBER DATA =======================
// ============================================================

// 'mock' membaca data/mock/*.mock.json; 'live' memanggil API_BASE_URL.
export const API_MODE = 'mock';

// Alamat dasar API sungguhan, tanpa garis miring di akhir.
export const API_BASE_URL = '';

// Jeda buatan agar perilaku loading di mode mock mirip API sungguhan.
export const MOCK_DELAY_MS = 150;
