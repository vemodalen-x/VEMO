"use strict";
const $ = (id) => document.getElementById(id);
const token = new URLSearchParams(location.hash.slice(1)).get("token") || sessionStorage.getItem("vemo-token") || "";
if (token) sessionStorage.setItem("vemo-token", token);
history.replaceState(null, "", location.pathname);
let preview = null;
let operation = "install";
let busy = false;

function notice(message, type = "") {
  $("notice").hidden = !message;
  $("notice").textContent = message;
  $("notice").className = type;
}
function setBusy(value) {
  busy = value;
  document.querySelectorAll("button, input, select").forEach((el) => { el.disabled = value; });
  if (!value) $("apply").disabled = !preview || !preview.ready;
}
async function api(path, data) {
  const response = await fetch(path, {
    method: data === undefined ? "GET" : "POST",
    headers: { "X-Vemo-Token": token, "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "请求失败，请重试。");
  return payload;
}
function inputs() {
  if (!$("target").reportValidity()) throw new Error("请输入项目绝对路径。");
  return { target: $("target").value.trim(), preset: $("preset").value, profile: $("profile").value };
}
function invalidate() {
  preview = null;
  $("preview-panel").hidden = true;
  $("apply").disabled = true;
  $("step-2").classList.remove("current");
  $("step-3").classList.remove("current");
}
function checks(container, rows) {
  container.replaceChildren();
  rows.forEach((row) => {
    const line = document.createElement("div");
    line.className = "check" + (row.ok ? "" : " fail");
    const name = document.createElement("span"); name.textContent = row.name;
    const value = document.createElement("span"); value.textContent = row.ok ? "✓ 通过" : "× 未通过";
    line.append(name, value); container.append(line);
  });
}
async function showPreview(kind) {
  try {
    const data = inputs();
    setBusy(true); invalidate(); $("result-panel").hidden = true;
    notice("正在检查环境与项目文件…", "busy");
    operation = kind;
    preview = await api(kind === "install" ? "/api/preview" : "/api/uninstall-preview", data);
    $("preview-panel").hidden = false;
    $("step-2").classList.add("current"); $("step-3").classList.remove("current");
    $("preview-title").textContent = kind === "install" ? "检查结果与变更预览" : "卸载变更预览";
    const changes = preview.actions.filter((row) => row.status !== "unchanged").length;
    $("summary").textContent = `${preview.actions.length} 个文件 · ${changes} 项操作 · ${preview.ready ? "可以继续" : "需要处理冲突"}`;
    checks($("environment"), preview.environment || []);
    $("conflicts").replaceChildren();
    const conflicts = preview.conflicts || preview.actions.filter((row) => row.conflict).map((row) => row.path + "：安装后已修改");
    conflicts.forEach((text) => { const li = document.createElement("li"); li.textContent = text; $("conflicts").append(li); });
    $("file-count").textContent = `(${preview.actions.length})`;
    $("file-list").replaceChildren();
    const labels = { create: "新增", merge: "合并", update: "更新", unchanged: "保持", conflict: "冲突", restore: "恢复原文件", remove: "移除" };
    preview.actions.forEach((row) => {
      const tr = document.createElement("tr");
      [row.path, row.conflict ? "冲突 · 保留" : labels[row.status]].forEach((value) => { const td = document.createElement("td"); td.textContent = value; tr.append(td); });
      $("file-list").append(tr);
    });
    $("apply").textContent = kind === "install" ? "确认安装并验证 →" : "确认卸载";
    $("preview-note").textContent = kind === "install" ? "合并项目入口与 Claude hooks，安装 Git 门禁与 CI 文件。已有文件冲突会阻止安装。" : "仅还原安装清单内的文件。任务、验收证据和 judge 记录保留；检测到后续修改会停止卸载。";
    notice(preview.ready ? "预览已就绪。确认文件清单后即可执行。" : "存在冲突，项目文件未被修改。请处理后重新预览。", preview.ready ? "" : "error");
  } catch (error) { notice(error.message, "error"); }
  finally { setBusy(false); }
}
async function job(path, data) {
  setBusy(true); $("result-panel").hidden = true;
  notice("正在执行并检查结果，请保持窗口打开…", "busy");
  try {
    const { job_id: id } = await api(path, data);
    let response;
    do {
      await new Promise((resolve) => setTimeout(resolve, 450));
      response = await api(`/api/jobs/${id}`);
    } while (response.status === "running");
    if (response.status === "failed") throw new Error(response.error);
    invalidate();
    const result = response.result;
    const verification = result.verification || result;
    const ok = verification.ready !== false;
    $("result-panel").hidden = false; $("step-2").classList.add("current"); $("step-3").classList.add("current");
    const titles = { installed: "安装完成，本地验证通过。", uninstalled: "卸载完成。", recovered: "中断操作已恢复。" };
    $("result-title").textContent = titles[result.mode] || (ok ? "安装检查通过。" : "检查发现问题。");
    $("result-description").textContent = result.preserved || (result.receipt ? `安装记录：${result.receipt}` : result.target);
    checks($("results"), verification.checks || []);
    $("evidence").hidden = !verification.checks;
    $("evidence-output").textContent = JSON.stringify(verification.checks || [], null, 2);
    $("next-actions").replaceChildren();
    if (verification.next) {
      const title = document.createElement("p"); title.textContent = "接下来，开始使用：";
      const list = document.createElement("ol");
      verification.next.forEach((text) => { const li = document.createElement("li"); li.textContent = text; list.append(li); });
      $("next-actions").append(title, list);
    }
    notice(ok ? "操作已完成，结果如下。" : "请根据失败项处理后重新检查。", ok ? "" : "error");
  } catch (error) {
    invalidate(); notice(error.message + "\n请处理原因后重试；若存在恢复日志，请使用“恢复中断操作”。", "error");
  } finally { setBusy(false); }
}
$("setup-form").addEventListener("submit", (event) => {
  event.preventDefault();
  if (busy) return;
  if ($("maintenance-controls").hidden) showPreview("install");
  else { try { job("/api/check", inputs()); } catch (error) { notice(error.message, "error"); } }
});
$("apply").addEventListener("click", () => { if (preview && preview.ready) job(`/api/${operation}`, { plan_id: preview.plan_id }); });
$("diagnose").addEventListener("click", () => { try { job("/api/check", inputs()); } catch (error) { notice(error.message, "error"); } });
$("uninstall-preview").addEventListener("click", () => showPreview("uninstall"));
$("recover").addEventListener("click", () => {
  try { const data = inputs(); if (confirm("将按恢复日志还原上次未完成操作的文件；后续修改的文件会保留。继续？")) job("/api/recover", data); }
  catch (error) { notice(error.message, "error"); }
});
["target", "preset", "profile"].forEach((id) => $(id).addEventListener("input", invalidate));
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
  if (busy) return;
  invalidate(); notice(""); $("result-panel").hidden = true;
  document.querySelectorAll("[data-view]").forEach((el) => el.classList.toggle("active", el === button));
  const install = button.dataset.view === "install";
  $("page-title").textContent = install ? "从一个项目开始。" : "让项目保持就绪。";
  $("page-description").textContent = install ? "几步接入可追溯的 AI 开发流程，让规则、执行和验收各就其位。" : "检查已安装组件，恢复中断操作，或安全移除框架。";
  ["install-options", "install-controls", "profile-help"].forEach((id) => { $(id).hidden = !install; });
  $("maintenance-controls").hidden = install;
}));
api("/api/info").then((data) => { $("version").textContent = data.version; }).catch((error) => notice(error.message, "error"));
