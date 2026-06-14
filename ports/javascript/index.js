#!/usr/bin/env node
// JavaScript port of the Cognis scan logic — same rules, same shape.
import { readdirSync, statSync, readFileSync, existsSync } from "fs";
import { join, resolve } from "path";
import { fileURLToPath } from "url";
const RULES = [["GEN-001","high","TODO"],["GEN-002","medium","FIXME"],["GEN-003","low","XXX"]];
function walk(p){ try{ return statSync(p).isDirectory()
  ? readdirSync(p).flatMap(f=>walk(join(p,f))) : [p]; }catch{ return []; } }
export function scan(target){
  if(typeof target !== "string" || target.trim() === ""){
    throw new TypeError("scan: target must be a non-empty string");
  }
  const findings=[];
  for(const f of walk(target)){
    let t=""; try{ t=readFileSync(f,"utf8"); }catch{ continue; }
    for(const [id,sev,needle] of RULES) if(t.includes(needle)) findings.push({id,sev,where:f});
  }
  return { tool:"awesome-cognis", findings, score: findings.length };
}
// Cross-platform main guard: fileURLToPath handles Windows drive letters and
// backslash vs forward-slash differences that break a raw string comparison.
if(fileURLToPath(import.meta.url)===resolve(process.argv[1]||"")){
  try {
    const rawTarget = process.argv[2] || ".";
    const target = resolve(rawTarget);
    if(!existsSync(target)){
      process.stderr.write(`error: path does not exist: ${rawTarget}\n`);
      process.exit(2);
    }
    console.log(JSON.stringify(scan(target),null,2));
  } catch(err) {
    process.stderr.write(`error: ${err.message}\n`);
    process.exit(1);
  }
}
