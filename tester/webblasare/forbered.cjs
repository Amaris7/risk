// Körs före webbläsartesterna: bygger en testsida med elak data (XSS-försök) av den riktiga mallen.
const { execFileSync } = require("node:child_process");
const path = require("node:path");

module.exports = () => {
  execFileSync("python3", [path.join(__dirname, "bygg_xss.py")], { stdio: "inherit" });
};
