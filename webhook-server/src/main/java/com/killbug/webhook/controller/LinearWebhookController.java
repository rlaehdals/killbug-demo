package com.killbug.webhook.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.webhook.exception.Response;
import com.killbug.webhook.service.LinearWebhookService;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@RestController
@RequiredArgsConstructor
public class LinearWebhookController {

    private final LinearWebhookService linearWebhookService;

    @GetMapping("/health")
    public ResponseEntity getHealth() {
        return Response.OK.getApiResponse(null);
    }

    @PostMapping("/linear/webhook")
    public ResponseEntity handleLinearWebhook(@RequestBody JsonNode payload) {
        linearWebhookService.handle(payload);

        return Response.OK.getApiResponse(null);
    }
}
