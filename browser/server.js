import puppeteer from 'puppeteer'

const { DISPLAY_WIDTH, DISPLAY_HEIGHT } = process.env

console.log("Launch chrome")
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
}
console.log("Open chrome", options)
const browser = await puppeteer.launch(options);

console.log("Open page")
const page = await browser.newPage();

console.log("Navigate")
// Navigate the page to a URL.
await page.goto('https://github.com/gbrian/codx-junior');
console.log("Navigate done")
// console.log("Page content", await page.content())
await new Promise(ok => setTimeout(ok, 10000))
await browser.close()