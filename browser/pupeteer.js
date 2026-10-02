const puppeteer = require('puppeteer-core');

const CDP_PORT = 9222;
const CHROME_PATH = process.env.CHROME_PATH || '/usr/bin/chromium';

let browser = null;

async function launchBrowser() {
  console.log(`[vibe] Launching Chrome with CDP port ${CDP_PORT}...`);

  browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: false,           // headed — visible on Debian desktop / VNC
    dumpio: true,
    args: [
        '--remote-debugging-port=9222',
        '--remote-debugging-address=0.0.0.0',
        '--remote-allow-origins=*',             // 👈 THIS fixes the Host header error
        '--disable-web-security',               // 👈 Helps with cross-container requests
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-gpu',
        '--disable-software-rasterizer', // Add this
        '--disable-dev-shm-usage',
    ],
    defaultViewport: null,     // use full window size
  });

  console.log(`[vibe] Chrome launched. CDP available at http://0.0.0.0:${CDP_PORT}`);

  browser.on('disconnected', () => {
    console.log('[vibe] Browser disconnected — restarting in 2s...');
    browser = null;
    setTimeout(launchBrowser, 2000);
  });

  browser.on('targetcreated', async (target) => {
    const url = target.url();
    // Ignore empty, internal, or non-web URLs
    if (!url || url === 'about:blank' || url.startsWith('chrome-')) return;
    
    console.log(`[vibe] [connection] New target: ${url}`);
  });
  
  browser.on('targetdestroyed', async (target) => {
    const url = target.url();
    const type = target.type();
    console.log(`[vibe] [connection] Target destroyed   — type: ${type} | url: ${url}`);
  });

  browser.on('targetchanged', async (target) => {
    const url = target.url();
    const type = target.type();
    console.log(`[vibe] [connection] Target navigated   — type: ${type} | url: ${url}`);
  });

  return browser;
}

// ── CDP connection polling — log active client count ──────────────────────────
const http = require('http');

function pollCDPClients() {
  const req = http.get(`http://0.0.0.0:${CDP_PORT}/json/version`, (res) => {
    // version endpoint responding = browser alive
  });
  req.on('error', () => {
    // browser not yet up — ignore
  });
  req.end();
}

// Poll every 10 seconds just to confirm browser is still reachable
setInterval(pollCDPClients, 10_000);

// ── Graceful shutdown ──────────────────────────────────────────────────────────
async function shutdown(signal) {
  console.log(`[vibe] ${signal} received — closing browser`);
  if (browser) {
    try {
      await browser.close();
    } catch (err) {
      console.error('[vibe] Error closing browser:', err.message);
    }
  }
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));

// ── Unhandled rejections — log but keep process alive ─────────────────────────
process.on('unhandledRejection', (reason) => {
  console.error('[vibe] Unhandled rejection (keeping server alive):', reason);
});

process.on('uncaughtException', (err) => {
  console.error('[vibe] Uncaught exception (keeping server alive):', err.message);
});

// ── Start ──────────────────────────────────────────────────────────────────────
(async () => {
  await launchBrowser();
  console.log('[vibe] Server is running. Waiting for CDP connections...');
})();