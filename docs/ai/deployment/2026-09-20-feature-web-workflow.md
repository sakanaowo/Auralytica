---
phase: deployment
title: Web workflow — Rollout nháp
description: Tài liệu deployment cho luồng web bốn bước, chưa nghiệm thu
---

# Web workflow — Rollout local

WFT08 chốt launcher Linux local: cài package bằng `uv tool install .`, chạy `auralytica` không đối số để mở loopback `127.0.0.1:8765` và trình duyệt. Có thể cài `packaging/auralytica.desktop` vào `~/.local/share/applications/`; desktop entry không mở terminal.

Launcher chỉ tái dùng cổng khi `/api/health` xác nhận đúng Auralytica API v1 và hash đường dẫn database trùng. Process lạ hoặc instance dùng database khác chỉ nhận lỗi hướng dẫn chọn cổng/đóng process; launcher không kill process. `--no-browser`, `--port` và `--database` là tùy chọn khởi động kỹ thuật, không phải CLI nghiệp vụ.

Trước nâng cấp vẫn cần sao lưu database và thư mục audio. WFT09 kiểm tra migration/rollback trên bản sao và chốt checklist phát hành; chưa deploy/push hoặc cam kết installer đa nền tảng.
