import { test, expect } from '@playwright/test';

test('find codx-junior GitHub project on Google and visit repository page', async ({ page }) => {
  // Go to Google
  await page.goto('https://www.google.com');

  // Accept cookies if prompted (optional, depending on region and settings)
  const acceptCookiesButton = await page.$('text="I agree"');
  if (acceptCookiesButton) {
    await acceptCookiesButton.click();
  }
await page.getByRole('button', { name: 'Alle akzeptieren' }).click();
  // Search for the "codx-junior repository"
  await page.getByLabel('Suche', { exact: true }).click();
  await page.getByLabel('Suche', { exact: true }).fill('codx-junior repository');
  await page.goto('https://www.google.com/search?q=codx-junior+repository&sca_esv=2e026587c10f4abc&source=hp&ei=-LyAZ_TuLIjAwPAPmaf8sAc&iflsig=AL9hbdgAAAAAZ4DLCAb_exp_MQt7-h3Webl3R6X8-VIr&ved=0ahUKEwj0yumbwuqKAxUIIBAIHZkTH3YQ4dUDCA4&uact=5&oq=codx-junior+repository&gs_lp=Egdnd3Mtd2l6IhZjb2R4LWp1bmlvciByZXBvc2l0b3J5MgUQIRigAUjMO1DpCFiKL3ABeACQAQCYAU6gAdQIqgECMjK4AQPIAQD4AQGYAhagAuwIqAIKwgIKEAAYAxjqAhiPAcICChAuGAMY6gIYjwHCAggQABiABBixA8ICERAuGIAEGLEDGNEDGIMBGMcBwgIFEC4YgATCAgsQLhiABBjRAxjHAcICDhAAGIAEGLEDGIMBGIoFwgILEC4YgAQYsQMYgwHCAg4QLhiABBixAxjRAxjHAcICCxAAGIAEGLEDGIMBwgIFEAAYgATCAg4QLhiABBixAxiDARiKBcICCBAuGIAEGLEDwgILEC4YgAQYxwEYrwHCAgcQABiABBgKwgIKEC4YgAQYsQMYCsICBBAAGB7CAgYQABgKGB7CAggQABiABBiiBMICCBAAGKIEGIkFwgIHECEYoAEYCpgDCfEFglwe_GD9e9-SBwIyMqAHilk&sclient=gws-wiz');
  // Click on the first search result link
  await page.click('a:has-text("codx-junior")');

  // Verify that the repository page is loaded
  await expect(page).toHaveURL(/github\.com\/.*codx-junior/);
  await expect(page).toHaveTitle(/codx-junior/);
});