#!/usr/bin/env node
/**
 * Lightweight TypeScript semantic analyzer for Mini-Wiki.
 *
 * Priority:
 * 1) Use TypeScript compiler API if available in target project.
 * 2) Fallback to regex extraction when TS API is unavailable.
 */

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const argv = process.argv.slice(2);
if (argv.length < 2) {
  process.stderr.write(
    "Usage: node ts_semantic_analyzer.mjs <projectRoot> <file1> [file2 ...]\n"
  );
  process.exit(1);
}

const projectRoot = path.resolve(argv[0]);
const files = argv
  .slice(1)
  .map((value) => path.resolve(value))
  .filter((value) => fs.existsSync(value) && fs.statSync(value).isFile());

function loadTypescript(projectDir) {
  const candidatePkg = path.join(projectDir, "package.json");
  try {
    const req = createRequire(candidatePkg);
    return req("typescript");
  } catch {
    try {
      return createRequire(import.meta.url)("typescript");
    } catch {
      return null;
    }
  }
}

function lineFromPos(text, pos) {
  return text.slice(0, pos).split("\n").length;
}

function stripProjectPrefix(fullPath) {
  const relative = path.relative(projectRoot, fullPath);
  return relative.split(path.sep).join("/");
}

function detectFlowHints(text) {
  const lower = text.toLowerCase();
  const hasState =
    lower.includes("zustand") ||
    lower.includes("state") ||
    lower.includes("store") ||
    lower.includes("redux") ||
    lower.includes("machine");
  const hasSequence =
    lower.includes("service") ||
    lower.includes("request") ||
    lower.includes("fetch") ||
    lower.includes("axios") ||
    lower.includes("client") ||
    lower.includes("api");
  return { hasState, hasSequence };
}

function analyzeWithTs(ts, fullPath) {
  const text = fs.readFileSync(fullPath, "utf8");
  const sourceFile = ts.createSourceFile(
    fullPath,
    text,
    ts.ScriptTarget.Latest,
    true
  );

  const entries = [];
  let classCount = 0;
  let interfaceCount = 0;
  const hints = detectFlowHints(text);

  const pushEntry = (name, type, node) => {
    if (!name) return;
    entries.push({
      name,
      type,
      file: stripProjectPrefix(fullPath),
      line: lineFromPos(text, node.getStart(sourceFile)),
      signature: text
        .slice(node.getStart(sourceFile), node.getEnd())
        .split("\n")[0]
        .trim(),
    });
  };

  const isExported = (node) =>
    !!node.modifiers &&
    node.modifiers.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword);

  sourceFile.forEachChild((node) => {
    if (ts.isFunctionDeclaration(node) && isExported(node)) {
      pushEntry(node.name?.text || "", "function", node);
      return;
    }
    if (ts.isClassDeclaration(node) && isExported(node)) {
      classCount += 1;
      pushEntry(node.name?.text || "", "class", node);
      return;
    }
    if (ts.isInterfaceDeclaration(node) && isExported(node)) {
      interfaceCount += 1;
      pushEntry(node.name?.text || "", "interface", node);
      return;
    }
    if (ts.isTypeAliasDeclaration(node) && isExported(node)) {
      interfaceCount += 1;
      pushEntry(node.name?.text || "", "type", node);
      return;
    }
    if (ts.isEnumDeclaration(node) && isExported(node)) {
      pushEntry(node.name?.text || "", "enum", node);
      return;
    }
    if (ts.isVariableStatement(node) && isExported(node)) {
      for (const decl of node.declarationList.declarations) {
        const name = decl.name && ts.isIdentifier(decl.name) ? decl.name.text : "";
        if (!name) continue;
        pushEntry(name, "const", decl);
      }
      return;
    }
    if (ts.isExportDeclaration(node) && node.exportClause && ts.isNamedExports(node.exportClause)) {
      for (const specifier of node.exportClause.elements) {
        const name = specifier.name.text;
        pushEntry(name, "re-export", specifier);
      }
    }
  });

  return { entries, classCount, interfaceCount, ...hints };
}

function analyzeWithRegex(fullPath) {
  const text = fs.readFileSync(fullPath, "utf8");
  const lines = text.split("\n");
  const entries = [];
  let classCount = 0;
  let interfaceCount = 0;
  const hints = detectFlowHints(text);

  const patterns = [
    { type: "function", regex: /^\s*export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)/ },
    { type: "class", regex: /^\s*export\s+class\s+([A-Za-z0-9_]+)/ },
    { type: "interface", regex: /^\s*export\s+interface\s+([A-Za-z0-9_]+)/ },
    { type: "type", regex: /^\s*export\s+type\s+([A-Za-z0-9_]+)/ },
    { type: "enum", regex: /^\s*export\s+enum\s+([A-Za-z0-9_]+)/ },
    { type: "const", regex: /^\s*export\s+const\s+([A-Za-z0-9_]+)/ },
  ];

  lines.forEach((line, index) => {
    for (const item of patterns) {
      const match = line.match(item.regex);
      if (!match) continue;
      if (item.type === "class") classCount += 1;
      if (item.type === "interface" || item.type === "type") interfaceCount += 1;
      entries.push({
        name: match[1],
        type: item.type,
        file: stripProjectPrefix(fullPath),
        line: index + 1,
        signature: line.trim(),
      });
      break;
    }
  });

  return { entries, classCount, interfaceCount, ...hints };
}

function analyzeFiles() {
  const ts = loadTypescript(projectRoot);
  const combined = {
    entries: [],
    classCount: 0,
    interfaceCount: 0,
    hasState: false,
    hasSequence: false,
    backend: ts ? "typescript-api" : "regex-fallback",
  };

  for (const fullPath of files) {
    try {
      const partial = ts ? analyzeWithTs(ts, fullPath) : analyzeWithRegex(fullPath);
      combined.entries.push(...partial.entries);
      combined.classCount += partial.classCount;
      combined.interfaceCount += partial.interfaceCount;
      combined.hasState = combined.hasState || partial.hasState;
      combined.hasSequence = combined.hasSequence || partial.hasSequence;
    } catch {
      const fallback = analyzeWithRegex(fullPath);
      combined.entries.push(...fallback.entries);
      combined.classCount += fallback.classCount;
      combined.interfaceCount += fallback.interfaceCount;
      combined.hasState = combined.hasState || fallback.hasState;
      combined.hasSequence = combined.hasSequence || fallback.hasSequence;
      combined.backend = "mixed-fallback";
    }
  }

  return combined;
}

const result = analyzeFiles();
process.stdout.write(`${JSON.stringify(result)}\n`);
