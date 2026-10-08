/* ============================================================
 * File      : mock-label.js
 * Proyek    : {{project_name}}
 * Deskripsi : Menampilkan label "Data contoh" setiap kali halaman
 *             menerima data dari mock, tanpa diatur per komponen.
 * Dibuat    : sistem skill website {{version}}, {{date}}
 * ============================================================ */

import { MOCK_EVENT } from './client.js';

// ============================================================
// ======================= LABEL MOCK =========================
// ============================================================

/**
 * Memasang pendengar yang memunculkan semua label data contoh di halaman.
 *
 * I.S. : Halaman memuat elemen [data-pd-mock-label] dengan atribut hidden.
 * F.S. : Saat data mock pertama diterima, semua label tersebut terlihat.
 *
 * @returns {void}
 */
export function watchMockData()
{
	document.addEventListener(MOCK_EVENT, showMockLabels, { once: true });
}

/**
 * Menghapus atribut hidden dari semua label data contoh.
 *
 * I.S. : Label data contoh tersembunyi.
 * F.S. : Label data contoh terlihat.
 *
 * @returns {void}
 */
function showMockLabels()
{
	const labels = document.querySelectorAll('[data-pd-mock-label]');

	labels.forEach((label) =>
	{
		label.hidden = false;
	});
}
