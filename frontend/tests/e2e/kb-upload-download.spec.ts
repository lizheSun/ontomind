import { test, expect } from './fixtures';
import { BACKEND_URL } from './fixtures';
import path from 'node:path';

test('upload markdown doc via API then download round-trip', async ({ request }) => {
  const login = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  expect(login.status()).toBe(200);
  const token = (await login.json()).data.access_token as string;

  const libs = await request.get(`${BACKEND_URL}/api/v1/knowledge-base/libraries`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(libs.status()).toBe(200);
  const libsBody = await libs.json();
  const docLib = libsBody.data.find((l: { code: string }) => l.code === 'document');
  expect(docLib).toBeTruthy();
  const libId = docLib.id as number;

  const fs = await import('node:fs/promises');
  const filePath = path.join(process.cwd(), 'tests/e2e/fixtures-doc.md');
  await fs.writeFile(filePath, '# e2e test doc\ncontent');
  const buffer = await fs.readFile(filePath);

  const upload = await request.post(`${BACKEND_URL}/api/v1/knowledge-base/documents/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      title_zh: `E2E 测试文档 ${Date.now()}`,
      library_id: String(libId),
      file: { name: 'e2e-doc.md', mimeType: 'text/markdown', buffer },
    },
  });
  expect(upload.status()).toBe(201);
  const docId = (await upload.json()).data.id as number;

  const download = await request.get(
    `${BACKEND_URL}/api/v1/knowledge-base/documents/${docId}/download`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  expect(download.status()).toBe(200);
  const bodyText = (await download.body()).toString('utf-8');
  expect(bodyText).toContain('e2e test doc');
});
