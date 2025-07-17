import express from 'express';
import { chromium } from 'playwright';

const app = express();
const port = 3000;

app.get('/', (_, res) => {
  res.send('Hello, Mr. BimbleBunch!');
});

app.get('/scrape', async (_, res) => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('https://example.com');
  const heading = await page.textContent('h1');
  await browser.close();
  res.json({ heading });
});

app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});

