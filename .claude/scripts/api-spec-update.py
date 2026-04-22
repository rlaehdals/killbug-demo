#!/usr/bin/env python3
# =============================================================================
# [API Spec] PostToolUse Hook
# Controller/DTO 파일 수정 시 docs/api-spec.md + docs/api-spec.yml 자동 갱신.
# 하네스 엔지니어링의 "개선(Feedback)" 레이어.
# =============================================================================
import json
import sys
import os
import re
import glob as globmod
from datetime import datetime


# ─── 설정 ───────────────────────────────────────────────

TRIGGER_PATHS = ["/controller/", "/request/", "/response/"]

HTTP_METHODS = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}

JAVA_TO_OPENAPI = {
    "String": ("string", None),
    "Long": ("integer", "int64"),
    "long": ("integer", "int64"),
    "Integer": ("integer", "int32"),
    "int": ("integer", "int32"),
    "Boolean": ("boolean", None),
    "boolean": ("boolean", None),
    "Double": ("number", "double"),
    "double": ("number", "double"),
    "LocalDateTime": ("string", "date-time"),
    "Instant": ("string", "date-time"),
    "JsonNode": ("object", None),
}


# ─── 유틸 ───────────────────────────────────────────────

def is_relevant(file_path):
    """Controller/DTO 파일 변경인지 확인."""
    return file_path.endswith(".java") and any(p in file_path for p in TRIGGER_PATHS)


def smart_split(s):
    """쉼표로 분리하되 <> () 안의 쉼표는 무시."""
    parts, depth, cur = [], 0, []
    for c in s:
        if c in "<(":
            depth += 1
        elif c in ">)":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    if cur:
        parts.append("".join(cur))
    return parts


# ─── Java 파싱 ──────────────────────────────────────────

def parse_base_path(content):
    """클래스 레벨 @RequestMapping 경로 추출."""
    m = re.search(r'@RequestMapping\s*\(\s*"([^"]*)"', content)
    return m.group(1) if m else ""


def parse_params(params_str):
    """메서드 파라미터 파싱."""
    params = []
    for part in smart_split(params_str):
        part = part.strip()
        if not part:
            continue

        p = {"location": "unknown", "type": "Object", "name": "?", "required": True}

        if "@PathVariable" in part:
            p["location"] = "path"
        elif "@RequestParam" in part:
            p["location"] = "query"
            if "required = false" in part or "required=false" in part:
                p["required"] = False
        elif "@RequestBody" in part:
            p["location"] = "body"
        elif "@RequestHeader" in part:
            p["location"] = "header"
            if "required = false" in part or "required=false" in part:
                p["required"] = False
            hm = re.search(r'value\s*=\s*"([^"]*)"', part)
            if hm:
                p["header_name"] = hm.group(1)
        else:
            continue

        # 어노테이션 제거 후 타입 + 이름 추출
        clean = re.sub(r"@\w+\s*(?:\([^)]*\))?\s*", "", part).strip()
        tokens = clean.split()
        if len(tokens) >= 2:
            p["type"] = tokens[-2]
            p["name"] = tokens[-1]
        elif tokens:
            p["name"] = tokens[0]

        params.append(p)
    return params


def parse_controller(file_path, module_name, project_dir):
    """Controller 파일에서 엔드포인트 정보 추출."""
    with open(file_path, "r") as f:
        lines = f.readlines()
    content = "".join(lines)

    cm = re.search(r"public class (\w+)", content)
    if not cm:
        return []
    class_name = cm.group(1)
    base_path = parse_base_path(content)

    endpoints = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for anno, http_method in HTTP_METHODS.items():
            if f"@{anno}" not in stripped:
                continue

            # 어노테이션에서 path 추출
            sub = ""
            pm = re.search(rf'@{anno}\s*\(.*?"([^"]*)"', stripped)
            if pm:
                sub = pm.group(1)

            full_path = base_path + sub
            if not full_path:
                full_path = base_path or "/"

            # 메서드 시그니처 수집 (다음 '{' 까지)
            sig = ""
            sig_end = i + 1
            for j in range(i + 1, min(i + 12, len(lines))):
                sig += " " + lines[j]
                sig_end = j
                if "{" in lines[j]:
                    break

            # 메서드 이름
            nm = re.search(r"public\s+\S+(?:<[^>]+>)?\s+(\w+)\s*\(", sig)
            method_name = nm.group(1) if nm else "unknown"

            # 파라미터
            pp = re.search(r"\((.*?)\)\s*(?:throws|\{)", sig, re.DOTALL)
            params = parse_params(pp.group(1)) if pp else []

            # Response DTO: 메서드 바디에서 탐색
            response_dto = None
            body_text = "".join(lines[sig_end:min(sig_end + 30, len(lines))])
            rm = re.search(r"List<(\w+Response)>", body_text)
            if not rm:
                rm = re.search(r"(\w+Response)\s+\w+\s*=", body_text)
            if rm:
                response_dto = rm.group(1)

            # consumes
            consumes = None
            cm2 = re.search(r"consumes\s*=\s*\w+\.(\w+)", stripped)
            if cm2:
                consumes = cm2.group(1)

            rel = os.path.relpath(file_path, project_dir)
            endpoints.append({
                "method": http_method,
                "path": full_path,
                "handler": f"{class_name}.{method_name}",
                "params": params,
                "source": f"{rel}:{i + 1}",
                "consumes": consumes,
                "module": module_name,
                "response_dto": response_dto,
            })
            break

    return endpoints


def parse_record(file_path, project_dir):
    """Java Record 파일에서 필드 정보 추출."""
    with open(file_path, "r") as f:
        content = f.read()
    m = re.search(r"public record (\w+)\s*\((.*?)\)\s*\{", content, re.DOTALL)
    if not m:
        return None
    name = m.group(1)
    fields = []
    for fld in smart_split(m.group(2)):
        fld = re.sub(r"@\w+\s*(?:\([^)]*\))?\s*", "", fld).strip()
        tokens = fld.split()
        if len(tokens) >= 2:
            fields.append({"type": tokens[0], "name": tokens[1]})
    return {
        "name": name,
        "fields": fields,
        "path": os.path.relpath(file_path, project_dir),
    }


# ─── 프로젝트 스캔 ──────────────────────────────────────

def scan_project(project_dir):
    """모든 모듈의 Controller/DTO를 스캔."""
    endpoints = []
    dtos = {}

    for ctrl_dir in globmod.glob(
        os.path.join(project_dir, "**/controller"), recursive=True
    ):
        if "/src/main/java/" not in ctrl_dir:
            continue
        module = os.path.basename(ctrl_dir.split("/src/main/java/")[0])

        # Controller 파싱
        for f in sorted(globmod.glob(os.path.join(ctrl_dir, "*.java"))):
            endpoints.extend(parse_controller(f, module, project_dir))

        # DTO 파싱 (request/ + response/)
        for sub in ("request", "response"):
            sub_dir = os.path.join(ctrl_dir, sub)
            if os.path.isdir(sub_dir):
                for f in sorted(globmod.glob(os.path.join(sub_dir, "*.java"))):
                    dto = parse_record(f, project_dir)
                    if dto:
                        dtos[dto["name"]] = dto

    return endpoints, dtos


# ─── Markdown 생성 ──────────────────────────────────────

def gen_markdown(endpoints, dtos):
    L = [
        "# KillBug API Specification\n",
        f"> Auto-generated by `api-spec-update.py` PostToolUse hook.",
        f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
    ]

    by_mod = {}
    for ep in endpoints:
        by_mod.setdefault(ep["module"], []).append(ep)

    for mod, eps in sorted(by_mod.items()):
        L.append(f"## {mod}\n")
        for ep in sorted(eps, key=lambda e: (e["path"], e["method"])):
            L.append(f"### {ep['method']} {ep['path']}\n")

            # 파라미터 테이블
            if ep["params"]:
                L.append("| 파라미터 | 위치 | 타입 | 필수 |")
                L.append("|---------|------|------|------|")
                for p in ep["params"]:
                    n = p.get("header_name", p["name"])
                    r = "Y" if p["required"] else "N"
                    L.append(f"| {n} | {p['location']} | `{p['type']}` | {r} |")
                L.append("")

            # Request Body DTO
            for p in ep["params"]:
                if p["location"] == "body" and p["type"] in dtos:
                    dto = dtos[p["type"]]
                    L.append(f"**Request Body**: `{p['type']}`\n")
                    L.append("| 필드 | 타입 |")
                    L.append("|------|------|")
                    for fld in dto["fields"]:
                        L.append(f"| {fld['name']} | `{fld['type']}` |")
                    L.append("")

            # Response DTO
            if ep.get("response_dto") and ep["response_dto"] in dtos:
                dto = dtos[ep["response_dto"]]
                L.append(f"**Response**: `{ep['response_dto']}`\n")
                L.append("| 필드 | 타입 |")
                L.append("|------|------|")
                for fld in dto["fields"]:
                    L.append(f"| {fld['name']} | `{fld['type']}` |")
                L.append("")

            # Source 참조
            L.append(f"> **Source**: `{ep['source']}`")

            # DTO 파일 참조
            refs = set()
            for p in ep["params"]:
                if p["type"] in dtos:
                    refs.add(dtos[p["type"]]["path"])
            if ep.get("response_dto") and ep["response_dto"] in dtos:
                refs.add(dtos[ep["response_dto"]]["path"])
            if refs:
                L.append("> **DTO**: " + ", ".join(f"`{r}`" for r in sorted(refs)))

            L.append("\n---\n")

    # DTO 레퍼런스
    if dtos:
        L.append("## DTO Reference\n")
        for name, dto in sorted(dtos.items()):
            L.append(f"### {name}\n")
            L.append(f"> `{dto['path']}`\n")
            L.append("| 필드 | 타입 |")
            L.append("|------|------|")
            for fld in dto["fields"]:
                L.append(f"| {fld['name']} | `{fld['type']}` |")
            L.append("")

    return "\n".join(L)


# ─── OpenAPI YAML 생성 ─────────────────────────────────

def oa_schema(java_type):
    """Java 타입 → OpenAPI YAML 스키마 라인."""
    if java_type.startswith("List<"):
        inner = java_type[5:-1]
        inner_t, inner_f = JAVA_TO_OPENAPI.get(inner, ("string", None))
        s = "type: array\n              items:\n"
        s += f"                type: {inner_t}"
        if inner_f:
            s += f"\n                format: {inner_f}"
        return s
    t, fmt = JAVA_TO_OPENAPI.get(java_type, ("string", None))
    s = f"type: {t}"
    if fmt:
        s += f"\n            format: {fmt}"
    return s


def gen_openapi(endpoints, dtos):
    L = [
        "openapi: '3.0.3'",
        "info:",
        "  title: KillBug API",
        "  description: Auto-generated by api-spec-update.py",
        "  version: '1.0.0'",
        "servers:",
        "  - url: http://localhost:8080",
        "    description: webhook-server",
        "paths:",
    ]

    by_path = {}
    for ep in endpoints:
        by_path.setdefault(ep["path"], []).append(ep)

    for path, eps in sorted(by_path.items()):
        L.append(f"  {path}:")
        for ep in eps:
            m = ep["method"].lower()
            L.append(f"    {m}:")
            L.append(f"      operationId: {ep['handler'].replace('.', '_')}")
            L.append(f"      summary: {ep['handler']}")

            # Parameters (path, query, header)
            non_body = [p for p in ep["params"] if p["location"] != "body"]
            if non_body:
                L.append("      parameters:")
                for p in non_body:
                    n = p.get("header_name", p["name"])
                    L.append(f"        - name: {n}")
                    L.append(f"          in: {p['location']}")
                    req = "true" if p["required"] else "false"
                    L.append(f"          required: {req}")
                    L.append("          schema:")
                    t, fmt = JAVA_TO_OPENAPI.get(p["type"], ("string", None))
                    L.append(f"            type: {t}")
                    if fmt:
                        L.append(f"            format: {fmt}")

            # Request body
            body_p = [p for p in ep["params"] if p["location"] == "body"]
            if body_p:
                bp = body_p[0]
                ct = "application/json"
                if ep.get("consumes") == "APPLICATION_FORM_URLENCODED_VALUE":
                    ct = "application/x-www-form-urlencoded"
                L.append("      requestBody:")
                L.append("        required: true")
                L.append("        content:")
                L.append(f"          {ct}:")
                L.append("            schema:")
                if bp["type"] in dtos:
                    L.append(
                        f"              $ref: '#/components/schemas/{bp['type']}'"
                    )
                else:
                    L.append("              type: object")

            # Response
            L.append("      responses:")
            L.append("        '200':")
            L.append("          description: OK")
            if ep.get("response_dto") and ep["response_dto"] in dtos:
                L.append("          content:")
                L.append("            application/json:")
                L.append("              schema:")
                L.append(
                    f"                $ref: '#/components/schemas/{ep['response_dto']}'"
                )

    # Components
    if dtos:
        L.append("components:")
        L.append("  schemas:")
        for name, dto in sorted(dtos.items()):
            L.append(f"    {name}:")
            L.append("      type: object")
            L.append("      properties:")
            for fld in dto["fields"]:
                L.append(f"        {fld['name']}:")
                t, fmt = JAVA_TO_OPENAPI.get(fld["type"], ("string", None))
                L.append(f"          type: {t}")
                if fmt:
                    L.append(f"          format: {fmt}")

    return "\n".join(L)


# ─── 메인 ───────────────────────────────────────────────

def main():
    hook_input = json.loads(sys.stdin.read())
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not is_relevant(file_path):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    endpoints, dtos = scan_project(project_dir)

    if not endpoints:
        return

    # docs/ 디렉토리 생성
    docs_dir = os.path.join(project_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    # Markdown + OpenAPI YAML 생성
    with open(os.path.join(docs_dir, "api-spec.md"), "w") as f:
        f.write(gen_markdown(endpoints, dtos))

    with open(os.path.join(docs_dir, "api-spec.yml"), "w") as f:
        f.write(gen_openapi(endpoints, dtos))

    n_ep = len(endpoints)
    n_dto = len(dtos)
    print(json.dumps({
        "hookSpecificOutput": (
            f"[API Spec] Updated: {n_ep} endpoints, {n_dto} DTOs "
            f"-> docs/api-spec.md + docs/api-spec.yml"
        )
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # PostToolUse 훅은 fail-open: 에러 시 작업 계속 진행
        pass
