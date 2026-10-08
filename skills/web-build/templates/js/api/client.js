/* ============================================================
 * File      : client.js
 * Proyek    : {{project_name}}
 * Deskripsi : Klien API. Satu-satunya file yang mengambil data;
 *             komponen memanggil request(), tidak pernah fetch() langsung.
 * Dibuat    : sistem skill website {{version}}, {{date}}
 * ============================================================ */

import { API_BASE_URL, API_MODE, MOCK_DELAY_MS } from './config.js';
import { ENDPOINTS } from './endpoints.js';

// ============================================================
// ========================= KONSTANTA ========================
// ============================================================

export const MOCK_EVENT = 'pd:mock-data';

const MOCK_FOLDER = '../../data/mock/';

// ============================================================
// ======================== API PUBLIK ========================
// ============================================================

/**
 * Mengambil data dari satu endpoint, dari mock atau API sungguhan sesuai API_MODE.
 *
 * I.S. : Endpoint terdaftar di ENDPOINTS; data belum diambil.
 * F.S. : Promise berisi data endpoint; di mode mock, MOCK_EVENT sudah dikirim.
 *
 * @param {string} name Nama endpoint di ENDPOINTS.
 * @param {object} params Parameter kueri, misalnya { page: 1, pageSize: 20 }.
 * @returns {Promise<unknown>} Data endpoint tanpa amplop.
 */
export async function request(name, params = {})
{
	const endpoint = ENDPOINTS[name];

	if (!endpoint)
	{
		throw new Error(`Endpoint tidak dikenal: ${name}`);
	}

	if (API_MODE === 'mock')
	{
		return requestMock(name, endpoint, params);
	}

	return requestLive(endpoint, params);
}

// ============================================================
// ========================== INTERNAL ========================
// ============================================================

/**
 * Membaca data contoh dari data/mock/ dan memastikan file itu memang data contoh.
 *
 * I.S. : File <mock>.mock.json ada dan berisi amplop dengan _mock bernilai true.
 * F.S. : Data hasil paginasi dikembalikan; MOCK_EVENT dikirim ke document.
 *
 * @param {string} name Nama endpoint, untuk detail event.
 * @param {object} endpoint Entri endpoint dari ENDPOINTS.
 * @param {object} params Parameter kueri.
 * @returns {Promise<unknown>} Data contoh.
 */
async function requestMock(name, endpoint, params)
{
	await wait(MOCK_DELAY_MS);

	const url = new URL(`${MOCK_FOLDER}${endpoint.mock}.mock.json`, import.meta.url);
	const response = await fetch(url);
	const body = await response.json();

	if (body._mock !== true)
	{
		throw new Error(`File mock tanpa penanda _mock: ${endpoint.mock}`);
	}

	document.dispatchEvent(new CustomEvent(MOCK_EVENT, { detail: { endpoint: name } }));

	return paginate(body.data, params);
}

/**
 * Memanggil API sungguhan dengan parameter sebagai query string.
 *
 * I.S. : API_BASE_URL terisi dan API mengembalikan JSON.
 * F.S. : Data JSON dari API dikembalikan; status selain 2xx melempar Error.
 *
 * @param {object} endpoint Entri endpoint dari ENDPOINTS.
 * @param {object} params Parameter kueri.
 * @returns {Promise<unknown>} Data dari API.
 */
async function requestLive(endpoint, params)
{
	const query = new URLSearchParams(params).toString();
	const url = `${API_BASE_URL}${endpoint.path}${query ? `?${query}` : ''}`;
	const response = await fetch(url, { method: endpoint.method });

	if (!response.ok)
	{
		throw new Error(`API ${endpoint.path} gagal: ${response.status}`);
	}

	return response.json();
}

/**
 * Meniru paginasi API pada data contoh berbentuk array.
 *
 * I.S. : data berupa array atau nilai lain; params boleh berisi page dan pageSize.
 * F.S. : Potongan array sesuai halaman, atau data apa adanya bila bukan array.
 *
 * @param {unknown} data Data contoh.
 * @param {object} params Parameter kueri.
 * @returns {unknown} Data yang sudah dipotong.
 */
function paginate(data, params)
{
	if (!Array.isArray(data) || !params.pageSize)
	{
		return data;
	}

	const page = params.page ?? 1;
	const start = (page - 1) * params.pageSize;

	return data.slice(start, start + params.pageSize);
}

/**
 * Menunggu beberapa milidetik.
 *
 * I.S. : ms bernilai nol atau lebih.
 * F.S. : Promise selesai setelah ms milidetik.
 *
 * @param {number} ms Lama tunggu dalam milidetik.
 * @returns {Promise<void>} Promise yang selesai setelah jeda.
 */
function wait(ms)
{
	return new Promise((resolve) =>
	{
		setTimeout(resolve, ms);
	});
}
