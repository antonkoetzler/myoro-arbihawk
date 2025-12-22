/**
 * Script to add missing translation keys to all locale files.
 *
 * Run this after adding new translation keys to ensure all languages are updated.
 *
 * Usage: bun run scripts/add-missing-translations.ts
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const localesDir = join(process.cwd(), 'src/lib/i18n/locales');
const enLocale = JSON.parse(
  readFileSync(join(localesDir, 'en.json'), 'utf-8')
);

const localeFiles = [
  'ar.json',
  'de.json',
  'es.json',
  'fr.json',
  'hi.json',
  'id.json',
  'it.json',
  'ja.json',
  'ko.json',
  'nl.json',
  'pl.json',
  'pt.json',
  'ru.json',
  'th.json',
  'tr.json',
  'vi.json',
  'zh.json',
  'zh_TW.json',
];

function addMissingKeys(target: any, source: any, path = ''): void {
  for (const key in source) {
    const currentPath = path ? `${path}.${key}` : key;
    if (typeof source[key] === 'object' && source[key] !== null) {
      if (!target[key]) {
        target[key] = {};
      }
      addMissingKeys(target[key], source[key], currentPath);
    } else {
      if (!(key in target)) {
        console.log(`[addMissingKeys]: Adding missing key: ${currentPath}`);
        target[key] = source[key]; // Use English as fallback
      }
    }
  }
}

for (const file of localeFiles) {
  const filePath = join(localesDir, file);
  const locale = JSON.parse(readFileSync(filePath, 'utf-8'));
  const original = JSON.stringify(locale, null, 2);

  addMissingKeys(locale, enLocale);

  const updated = JSON.stringify(locale, null, 2);
  if (original !== updated) {
    writeFileSync(filePath, updated, 'utf-8');
    console.log(`[add-missing-translations]: ✅ Updated ${file}`);
  } else {
    console.log(`[add-missing-translations]: ✓ ${file} is up to date`);
  }
}

console.log('[add-missing-translations]: \n✨ All locale files updated!');

