const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const sourceDir = "./website/static/js";
const targetDir = "./staticfiles/js";

function copyFile(source, target) {
  const targetDir = path.dirname(target);
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }
  fs.copyFileSync(source, target);
}

function compileJSX(source, target) {
  const targetDir = path.dirname(target);
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }
  execSync(`npx babel ${source} --out-file ${target}`);
}

function processDirectory(dir) {
  const files = fs.readdirSync(dir);

  files.forEach((file) => {
    const sourcePath = path.join(dir, file);
    const targetPath = path.join(
      targetDir,
      path.relative(sourceDir, sourcePath),
    );

    if (fs.statSync(sourcePath).isDirectory()) {
      processDirectory(sourcePath);
    } else {
      if (path.extname(file) === ".jsx") {
        compileJSX(sourcePath, targetPath.replace(".jsx", ".js"));
      } else {
        copyFile(sourcePath, targetPath);
      }
    }
  });
}

// Create target directory if it doesn't exist
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
}

processDirectory(sourceDir);

console.log("Build completed successfully!");
