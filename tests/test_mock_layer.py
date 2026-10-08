# ============================================================
# File      : test_mock_layer.py
# Deskripsi : Pengujian unit untuk lapisan mock API (client.js dan mock-label.js)
#             melalui Node.js dengan stub fetch dan simulasi DOM.
# ============================================================

import subprocess
import pytest
from conftest import copy_fixture, run_script
from lib import io


@pytest.mark.node
def test_mock_layer_behavior_in_node(projects_dir):
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")

    site_dir = proj / "site"

    # Siapkan endpoints.js dan mock file yang valid
    ep_file = site_dir / "js" / "api" / "endpoints.js"
    io.write_text(
        ep_file,
        """export const ENDPOINTS = {
\ttestMetric: { method: 'GET', path: '/metrics', mock: 'test-metric' },
};
""",
    )

    mock_file = site_dir / "data" / "mock" / "test-metric.mock.json"
    io.write_json(
        mock_file,
        {
            "_mock": True,
            "endpoint": "GET /metrics",
            "generated_by": "pd-web-skills 0.1",
            "data": [{"val": 100}],
        },
    )

    # Buat skrip uji Node.js yang memverifikasi:
    # 1. request() berhasil pada file mock dengan _mock: true
    # 2. watchMockData() membuat elemen mock label terlihat
    # 3. file mock tanpa _mock: true melempar error
    node_test_script = site_dir / "test_client.mjs"
    io.write_text(
        node_test_script,
        """import assert from 'node:assert';
import { request, MOCK_EVENT } from './js/api/client.js';
import { watchMockData } from './js/api/mock-label.js';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Simulasi minimal DOM & CustomEvent
class MockElement {
	constructor() { this.hidden = true; }
}
const mockLabel = new MockElement();

const listeners = [];
globalThis.document = {
	addEventListener: (type, fn, opts) => listeners.push({ type, fn, opts }),
	dispatchEvent: (evt) => {
		for (const l of listeners) {
			if (l.type === evt.type) l.fn(evt);
		}
	},
	querySelectorAll: (sel) => sel === '[data-pd-mock-label]' ? [mockLabel] : []
};
globalThis.CustomEvent = class CustomEvent {
	constructor(type, init) { this.type = type; this.detail = init?.detail; }
};

// Stub fetch lokal untuk membaca file dari disk
globalThis.fetch = async (url) => {
	const filePath = fileURLToPath(url);
	const text = fs.readFileSync(filePath, 'utf-8');
	return {
		ok: true,
		json: async () => JSON.parse(text)
	};
};

// 1. Pasang watchMockData
watchMockData();
assert.strictEqual(mockLabel.hidden, true, 'Label harus tersembunyi di awal');

// 2. Panggil request() untuk data valid
const data = await request('testMetric');
assert.deepStrictEqual(data, [{ val: 100 }], 'Data mock harus sesuai');
assert.strictEqual(mockLabel.hidden, false, 'Label harus muncul setelah event mock');

// 3. Tes bahwa file tanpa _mock: true melempar error
const badMockPath = path.join(__dirname, 'data/mock/test-metric.mock.json');
fs.writeFileSync(badMockPath, JSON.stringify({ _mock: false, data: [] }));

let threw = false;
try {
	await request('testMetric');
} catch (err) {
	threw = true;
	assert(err.message.includes('_mock'), 'Pesan error harus menyebutkan _mock');
}
assert.strictEqual(threw, true, 'Mock tanpa _mock: true harus melempar error');

console.log('MOCK_LAYER_TEST_OK');
""",
    )

    cmd = ["node", str(node_test_script)]
    res = subprocess.run(cmd, cwd=site_dir, capture_output=True, text=True, shell=True)
    assert res.returncode == 0, f"Node test gagal:\n{res.stdout}\n{res.stderr}"
    assert "MOCK_LAYER_TEST_OK" in res.stdout
