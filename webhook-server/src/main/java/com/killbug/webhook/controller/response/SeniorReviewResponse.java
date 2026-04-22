package com.killbug.webhook.controller.response;

import java.time.LocalDateTime;

import lombok.Builder;

@Builder
public record SeniorReviewResponse(Long id, String name, String review, String module, LocalDateTime createdAt) {}
