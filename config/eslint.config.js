// ============================================================
// File      : eslint.config.js
// Deskripsi : Aturan format dan kualitas JavaScript keluaran sistem.
//             ESLint memegang seluruh format JS (gaya Allman).
// ============================================================

import stylistic from '@stylistic/eslint-plugin';
import jsdoc from 'eslint-plugin-jsdoc';
import globals from 'globals';

const BLOCK_STATEMENTS = ['if', 'for', 'while', 'do', 'switch', 'try', 'function', 'class'];

export default [
	{
		files: ['**/*.js'],
		languageOptions: {
			ecmaVersion: 2023,
			sourceType: 'module',
			globals: globals.browser,
		},
		plugins: {
			'@stylistic': stylistic,
			jsdoc,
		},
		rules: {
			// Format: tab, Allman, satu pernyataan per baris, baris kosong di sekitar blok
			'@stylistic/indent': ['error', 'tab'],
			'@stylistic/brace-style': ['error', 'allman', { allowSingleLine: false }],
			'@stylistic/max-len': ['error', { code: 100, tabWidth: 4, ignoreUrls: true }],
			'@stylistic/max-statements-per-line': ['error', { max: 1 }],
			'@stylistic/no-trailing-spaces': 'error',
			'@stylistic/no-multiple-empty-lines': ['error', { max: 1 }],
			'@stylistic/padding-line-between-statements': [
				'error',
				{ blankLine: 'always', prev: '*', next: BLOCK_STATEMENTS },
				{ blankLine: 'always', prev: BLOCK_STATEMENTS, next: '*' },
			],
			'@stylistic/lines-between-class-members': ['error', 'always'],
			'@stylistic/quotes': ['error', 'single'],
			'@stylistic/semi': ['error', 'always'],

			// Komentar: di atas baris, tanpa TODO
			'@stylistic/line-comment-position': ['error', { position: 'above' }],
			'@stylistic/spaced-comment': ['error', 'always'],
			'no-inline-comments': 'error',
			'no-warning-comments': ['error', { terms: ['todo', 'fixme', 'xxx'], location: 'anywhere' }],

			// Struktur dan keterbacaan
			curly: ['error', 'all'],
			'max-lines-per-function': ['error', { max: 30, skipBlankLines: true, skipComments: true }],
			'max-depth': ['error', 4],
			'default-case': 'error',
			'prefer-const': 'error',
			'no-var': 'error',
			'no-console': 'error',
			camelcase: ['error', { properties: 'never' }],

			// Dokumentasi fungsi (isi I.S./F.S. dicek oleh check.py)
			'jsdoc/require-jsdoc': [
				'error',
				{
					require: {
						FunctionDeclaration: true,
						FunctionExpression: true,
						ArrowFunctionExpression: true,
						MethodDefinition: true,
					},
				},
			],
			'jsdoc/require-description': 'error',
			'jsdoc/require-param': 'error',
			'jsdoc/require-param-type': 'error',
			'jsdoc/require-returns': ['error', { forceRequireReturn: true }],
		},
	},
];
