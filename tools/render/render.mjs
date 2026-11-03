/* ============================================================
 * File      : render.mjs
 * Proyek    : ScaffolDev
 * Deskripsi : Membuka setiap halaman situs di Chromium: screenshot 1440 dan
 *             390 px, axe-core, lebar gulir di HP, serta sidik warna dan
 *             tata letak dari DOM. Dipanggil oleh tools/render_check.py.
 * ============================================================ */

import { readFileSync, createReadStream, existsSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { createRequire } from 'node:module';
import { extname, join, normalize, resolve } from 'node:path';
import { chromium } from 'playwright-core';

const require = createRequire(import.meta.url);

// ============================================================
// ======================= SERVER STATIS ======================
// ============================================================

const TYPES = {
	'.html': 'text/html; charset=utf-8',
	'.css': 'text/css; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.mjs': 'text/javascript; charset=utf-8',
	'.json': 'application/json; charset=utf-8',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.webp': 'image/webp',
};

/**
 * Menyajikan folder situs lewat HTTP lokal, karena modul ES dan fetch() tidak jalan di file://.
 *
 * I.S. : root adalah folder situs yang ada.
 * F.S. : Server mendengarkan di port acak 127.0.0.1; Promise berisi server dan URL dasarnya.
 *
 * @param {string} root Folder situs.
 * @returns {Promise<{server: import('node:http').Server, base: string}>} Server dan URL dasar.
 */
function serve(root)
{
	const server = createServer((request, response) =>
	{
		const path = normalize(decodeURIComponent(new URL(request.url, 'http://x').pathname));
		const file = join(root, path.endsWith('/') ? `${path}index.html` : path);

		if (!resolve(file).startsWith(resolve(root)) || !existsSync(file) || !statSync(file).isFile())
		{
			response.writeHead(404).end();
			return;
		}

		response.writeHead(200, { 'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream' });
		createReadStream(file).pipe(response);
	});

	return new Promise((done) =>
	{
		server.listen(0, '127.0.0.1', () => done({ server, base: `http://127.0.0.1:${server.address().port}/` }));
	});
}

// ============================================================
// ====================== SIDIK HALAMAN =======================
// ============================================================

/**
 * Mengambil sidik halaman di dalam browser: pohon landmark dan sampel warna yang tampak.
 *
 * I.S. : Halaman sudah dimuat; viewport setinggi halaman agar semua titik bisa diambil.
 * F.S. : Objek {tree, colors} dikembalikan; colors berisi [r, g, b, bobot].
 *
 * @returns {{tree: Array, colors: Array<Array<number>>}} Sidik halaman.
 */
function fingerprint()
{
	const KEEP = new Set(['HEADER', 'NAV', 'MAIN', 'FOOTER', 'SECTION', 'ASIDE', 'ARTICLE',
		'FORM', 'TABLE', 'FIGURE', 'H1', 'H2', 'H3', 'UL', 'OL', 'DL', 'IMG', 'CANVAS']);

	/**
	 * Menyusun pohon landmark dari satu elemen.
	 *
	 * I.S. : element adalah elemen DOM.
	 * F.S. : Daftar simpul [label, anak] untuk keturunan yang dipertahankan.
	 *
	 * @param {Element} element Elemen awal.
	 * @returns {Array} Daftar simpul.
	 */
	function walk(element)
	{
		const nodes = [];

		for (const child of element.children)
		{
			const below = walk(child);

			if (KEEP.has(child.tagName) || child.dataset.pdPattern)
			{
				const label = child.tagName.toLowerCase() + (child.dataset.pdPattern ? `:${child.dataset.pdPattern}` : '');
				nodes.push([label, below]);
			}
			else
			{
				nodes.push(...below);
			}
		}
		return nodes;
	}

	/**
	 * Mencari warna latar yang benar-benar tampak di bawah satu elemen.
	 *
	 * I.S. : element adalah elemen DOM.
	 * F.S. : [r, g, b] latar pertama yang tidak transparan, atau putih.
	 *
	 * @param {Element} element Elemen di titik sampel.
	 * @returns {Array<number>} Warna RGB.
	 */
	function background(element)
	{
		for (let node = element; node; node = node.parentElement)
		{
			const match = getComputedStyle(node).backgroundColor.match(/[\d.]+/g);

			if (match && (match.length < 4 || Number(match[3]) > 0.5))
			{
				return match.slice(0, 3).map(Number);
			}
		}
		return [255, 255, 255];
	}

	const colors = [];
	const width = document.documentElement.clientWidth;
	const height = Math.min(document.documentElement.scrollHeight, 8000);

	for (let y = 10; y < height; y += 40)
	{
		for (let x = 10; x < width; x += 40)
		{
			const element = document.elementFromPoint(x, y);

			if (element)
			{
				colors.push([...background(element), 1]);
			}
		}
	}

	for (const element of document.body.querySelectorAll('*'))
	{
		const own = [...element.childNodes].filter((node) => node.nodeType === 3).map((node) => node.textContent.trim()).join('');

		if (own && element.getClientRects().length)
		{
			colors.push([...getComputedStyle(element).color.match(/[\d.]+/g).slice(0, 3).map(Number), own.length / 20]);
		}
	}

	return { tree: walk(document.body), colors };
}

// ============================================================
// ========================== UTAMA ===========================
// ============================================================

/**
 * Memeriksa satu halaman di dua lebar layar.
 *
 * I.S. : browser terbuka; base adalah URL server situs; out adalah folder screenshot.
 * F.S. : Screenshot tertulis; hasil axe, lebar gulir di 390 px, dan sidik halaman dikembalikan.
 *
 * @param {import('playwright-core').Browser} browser Browser.
 * @param {string} base URL dasar situs.
 * @param {string} page Path halaman relatif.
 * @param {string} out Folder screenshot.
 * @param {string} axeSource Isi axe.min.js.
 * @returns {Promise<object>} Hasil halaman.
 */
async function checkPage(browser, base, page, out, axeSource)
{
	const name = page.replace(/[\\/]/g, '_').replace(/\.html$/, '');
	const result = { page, errors: [] };

	for (const width of [1440, 390])
	{
		const tab = await browser.newPage({ viewport: { width, height: 900 } });
		tab.on('pageerror', (error) => result.errors.push(error.message));
		tab.on('console', (message) => message.type() === 'error' && result.errors.push(message.text()));
		await tab.goto(base + page, { waitUntil: 'networkidle' });
		await tab.waitForTimeout(300);
		await tab.screenshot({ path: join(out, `${name}-${width}.png`), fullPage: true });

		if (width === 390)
		{
			result.scrollWidth = await tab.evaluate(() => document.documentElement.scrollWidth);
		}
		else
		{
			await tab.addScriptTag({ content: axeSource });
			result.axe = await tab.evaluate(async () => (await window.axe.run(document, { resultTypes: ['violations'] }))
				.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length, target: v.nodes[0]?.target.join(' ') })));
			const full = await tab.evaluate(() => Math.min(document.documentElement.scrollHeight, 8000));
			await tab.setViewportSize({ width, height: full });
			result.fingerprint = await tab.evaluate(fingerprint);
		}

		await tab.close();
	}
	return result;
}

const [site, out, browserPath, ...pages] = process.argv.slice(2);
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const { server, base } = await serve(site);
const browser = await chromium.launch({ executablePath: browserPath });

try
{
	const results = [];

	for (const page of pages)
	{
		results.push(await checkPage(browser, base, page, out, axeSource));
	}
	process.stdout.write(JSON.stringify(results));
}
finally
{
	await browser.close();
	server.close();
}
