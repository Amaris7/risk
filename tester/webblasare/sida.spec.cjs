// Webbläsartester för index.html. Körs i både datorbredd och mobilbredd (se playwright.config.cjs).
const { test, expect } = require("@playwright/test");

const antal = async page => parseInt((await page.locator("#count").textContent()).replace(/\D/g, ""), 10);

// Samla fel i webbläsaren: JavaScript-fel och CSP-blockeringar ska aldrig förekomma
test.beforeEach(async ({ page }, info) => {
  info.fel = [];
  page.on("pageerror", e => info.fel.push(String(e)));
  page.on("console", m => { if (m.type() === "error" && !/annonstext\.json|404/.test(m.text())) info.fel.push(m.text()); });
});
test.afterEach(async ({}, info) => {
  if (info.fel !== null) expect(info.fel, "fel i webbläsarens konsol").toEqual([]);
});

test("sidan laddar med titel, nyckeltal och översikt", async ({ page }) => {
  await page.goto("/index.html");
  await expect(page).toHaveTitle("Karriär i riskhantering");
  await expect(page.locator("#v-oversikt")).toBeVisible();
  await expect(page.locator("#facts b").first()).toHaveText(/\d/);
});

test("alla flikar går att nå, i mobilen via Mer-menyn", async ({ page }) => {
  await page.goto("/index.html");
  for (const [hash, rubrik] of [["utbildningen", "Riskhantering i samhället"], ["valbara", "Valbara kurser"], ["kalender", "Kurskalender"], ["yrkesroller", "Yrkesroller"],
    ["annonser", "Jobbannonser"], ["efterfragat", "Vad efterfrågas"], ["om", "Om datan"]]) {
    const flik = page.locator(`#tabs a[href="#${hash}"]`);
    if (await flik.isVisible()) {
      await flik.click();
    } else {
      await page.locator("#tabmore-btn").click();
      await page.locator(`#tabmenu a[href="#${hash}"]`).click();
      await expect(page.locator("#tabmenu")).toBeHidden();
    }
    await expect(page.locator(`#v-${hash} h2`)).toContainText(rubrik);
    await expect(page.locator(`#tabs a[href="#${hash}"]`)).toBeVisible(); // aktiv flik syns alltid
  }
});

test("flikarna får plats utan sidledsskroll", async ({ page }) => {
  await page.goto("/index.html#annonser");
  const bred = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(bred, "sidan skrollar i sidled").toBe(false);
});

test("filter och sökning minskar antalet annonser", async ({ page, isMobile }) => {
  await page.goto("/index.html#annonser");
  const alla = await antal(page);
  expect(alla).toBeGreaterThan(200);
  if (isMobile) await page.locator("#ftoggle").click();
  await page.locator("#f-status button[data-v='aktuell']").click();
  const aktuella = await antal(page);
  expect(aktuella).toBeLessThan(alla);
  await page.locator("#f-lan").selectOption("Stockholms län");
  expect(await antal(page)).toBeLessThanOrEqual(aktuella);
  await expect(page.locator(".ad").first()).toContainText("Stockholms län");
  if (isMobile) await expect(page.locator("#fcount")).toHaveText("2");
  await page.locator("#reset").click();
  expect(await antal(page)).toBe(alla);
  await page.locator("#f-q").fill("beredskapssamordnare");
  await expect(page.locator("#count")).toContainText("hela annonstexten");
  const traffar = await antal(page);
  expect(traffar).toBeGreaterThan(0);
  expect(traffar).toBeLessThan(alla);
});

test("sökordsräknaren visar antal och leder till annonserna", async ({ page }) => {
  await page.goto("/index.html#efterfragat");
  await page.locator("#kws-q").fill("krisledning");
  const tal = page.locator(".kws-big b").first();
  await expect(tal).toHaveText(/^\d[\d\s]*$/);
  const n = parseInt((await tal.textContent()).replace(/\D/g, ""), 10);
  expect(n).toBeGreaterThan(0);
  await page.locator("#kws-go").click();
  await expect(page).toHaveURL(/#annonser$/);
  expect(await antal(page)).toBe(n);
});

test("sökning med specialtecken kraschar inte", async ({ page }) => {
  await page.goto("/index.html#efterfragat");
  for (const q of ["(", "[a-z]+", ".*", "\\"]) {
    await page.locator("#kws-q").fill(q);
    await expect(page.locator("#kws-res")).not.toBeEmpty();
  }
});

test("kalendern visar händelser med kursnamn och inga kurskoder", async ({ page }) => {
  await page.goto("/index.html#kalender");
  await page.locator("#kal-tid button[data-v='alla']").click();
  const ev = page.locator(".ev");
  expect(await ev.count()).toBeGreaterThan(0);
  // Rubriker och etiketter ska visa kursnamn. Lärarnas anteckningar under "Mer information" får nämna koder.
  const synligt = (await page.locator(".ev .t, .ev .chips, .kal-next").allTextContents()).join(" ");
  expect(synligt).not.toMatch(/\bRHA[DE]\d{2}\b/);
  expect(synligt).not.toContain("Övrigt");
});

test("annonslänkar går bara till Platsbanken och öppnas säkert", async ({ page }) => {
  await page.goto("/index.html#annonser");
  const lankar = page.locator(".ad h3 a");
  const n = Math.min(await lankar.count(), 20);
  for (let i = 0; i < n; i++) {
    await expect(lankar.nth(i)).toHaveAttribute("href", /^https:\/\/arbetsformedlingen\.se\/platsbanken\/annonser\//);
    await expect(lankar.nth(i)).toHaveAttribute("rel", /noopener/);
  }
});

test("alla annonskort har samma struktur med krav och matchning", async ({ page }) => {
  await page.goto("/index.html#annonser");
  const kort = page.locator(".ad");
  const n = await kort.count();
  expect(n).toBeGreaterThan(10);
  for (const del of [".head h3", ".right .chip", ".ex", ".adfacts dt:text('Krav')", ".adfacts dt:text('Passar')"]) {
    expect(await page.locator(`.ad ${del}`).count(), del).toBe(n);
  }
});

test("yrkesrollerna visar hela titlar och vanliga krav", async ({ page }) => {
  await page.goto("/index.html#yrkesroller");
  await expect(page.locator(".role dd").first()).not.toContainText(/·\s*Säkerhets\s*(·|$)/);
  expect(await page.locator(".role .kravlist").count()).toBe(await page.locator(".role").count());
});

test("valbara kurser visar kompetensprofil och leder till annonser", async ({ page }) => {
  await page.goto("/index.html#valbara");
  expect(await page.locator(".komp-r").count()).toBe(8);
  expect(await page.locator(".vkurs").count()).toBe(5);
  expect(await page.locator(".komp-r").first().locator(".kbar").count()).toBe(4);
  await expect(page.locator(".komp-r .kbar .kb-n").first()).toHaveText(/^\d[\d\s]* av alla \d[\d\s]* annonser nämner det$/);
  await expect(page.locator(".komp-r").first().locator(".kbar .kb-n").nth(3)).toHaveText(/^\d+ av \d+ klimatannonser nämner det, [\d,]+ % av alla \d[\d\s]* annonser$/);
  await expect(page.locator("#komp-klim-not")).toContainText("procentenheter");
  await expect(page.locator(".vkurs h3").first()).toHaveText("Klimatanpassning och riskreducering");
  await expect(page.locator("#v-valbara")).not.toContainText(/\bRHA[DE]\d{2}\b|MVAE/);
  await page.locator(".vkurs button.go").first().click();
  await expect(page).toHaveURL(/#annonser$/);
  await expect(page.locator("#count")).toContainText("hela annonstexten");
  expect(await antal(page)).toBeGreaterThan(50);
});

test("färgtemat går att välja och sparas", async ({ page }) => {
  await page.goto("/index.html");
  const html = page.locator("html"), knapp = page.locator("#theme-btn");
  await expect(knapp).toHaveAttribute("data-mode", "auto");
  await knapp.click();
  await expect(html).toHaveAttribute("data-theme", "light");
  await knapp.click();
  await expect(html).toHaveAttribute("data-theme", "dark");
  const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(bg).toBe("rgb(13, 22, 25)");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", "dark");
  await knapp.click();
  await expect(html).not.toHaveAttribute("data-theme", /./);
  await expect(knapp).toHaveAttribute("data-mode", "auto");
});

test.describe("säkerhet: elak data körs inte (XSS)", () => {
  test("ingen injicerad kod körs och texten visas som text", async ({ page }, info) => {
    info.fel = null; // testsidan saknar annonstext.json med flit
    const dialoger = [];
    page.on("dialog", d => { dialoger.push(d.message()); d.dismiss(); });
    for (const hash of ["annonser", "kalender", "yrkesroller", "efterfragat", "oversikt"]) {
      await page.goto(`/tester/webblasare/_xss.html#${hash}`);
      if (hash === "efterfragat") await page.locator("#kws-q").fill("beredskapssamordnare");
      if (hash === "kalender") await page.locator("#kal-tid button[data-v='alla']").click();
      await page.waitForTimeout(200);
      expect(await page.evaluate(() => window.__xss), `kod kördes på fliken ${hash}`).toBeUndefined();
      expect(await page.locator("main img, main script").count(), `injicerade element på fliken ${hash}`).toBe(0);
    }
    expect(dialoger).toEqual([]);
    await page.goto("/tester/webblasare/_xss.html#annonser");
    await expect(page.locator(".ad h3")).toContainText("<img src=x");
    await expect(page.locator(".ad h3 a"), "javascript:-länk ska inte bli en länk").toHaveCount(0);
  });
});
