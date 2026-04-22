package com.killbug.webhook.controller.response;

import java.time.LocalDateTime;

import lombok.Builder;

@Builder
public record RoleDataResponse(Long id, String name, String content, String extra, LocalDateTime createdAt) {}
