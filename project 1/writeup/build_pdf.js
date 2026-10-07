// Print writeup.html to writeup.pdf with headless Chromium (Playwright).
//   pandoc writeup.md -s --mathml --embed-resources -c style.css -o writeup.html
//   node build_pdf.js
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
  });
  const page = await browser.newPage();
  await page.goto("file://" + path.resolve(__dirname, "writeup.html"));
  await page.pdf({
    path: path.resolve(__dirname, "writeup.pdf"),
    format: "Letter",
    margin: { top: "0.8in", bottom: "0.8in", left: "0.75in", right: "0.75in" },
    displayHeaderFooter: true,
    headerTemplate: "<span></span>",
    footerTemplate:
      '<div style="font-size:8pt;width:100%;text-align:center;color:#555">' +
      '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    printBackground: true,
  });
  await browser.close();
})();
