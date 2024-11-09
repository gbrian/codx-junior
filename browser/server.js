import express from 'express';
import puppeteer from 'puppeteer';

const app = express();
const PORT = process.env.PORT || 3000;

const { DISPLAY_WIDTH, DISPLAY_HEIGHT } = process.env;

app.get('/start', async (req, res) => {
  try {
    console.log("Launch chrome");
    const options = {
      headless: false,
      defaultViewport: {
        width: parseInt(DISPLAY_WIDTH, 10),
        height: parseInt(DISPLAY_HEIGHT, 10)
      },
      args: [
        "--no-sandbox",
        "--start-fullscreen",
        `--window-size=${DISPLAY_WIDTH},${DISPLAY_HEIGHT}`,
        '--window-position="0,0"'
      ]
    };
    
    console.log("Open chrome", options);
    const browser = await puppeteer.launch(options);

    console.log("Open page");
    const page = await browser.newPage();

    console.log("Navigate");
    await page.goto('https://github.com/gbrian/codx-junior');
    console.log("Navigate done");
    await new Promise(ok => setTimeout(ok, 10000));
    await browser.close();

    res.send('Browser session started and closed after 10 seconds.');
  } catch (error) {
    console.error('Error starting browser session:', error);
    res.status(500).send('Failed to start browser session.');
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});