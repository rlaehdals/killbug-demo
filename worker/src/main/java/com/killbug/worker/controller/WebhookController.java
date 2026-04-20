package com.killbug.worker.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.databind.JsonNode;
import com.killbug.worker.exception.Response;
import com.killbug.worker.service.WebhookDispatchService;

import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
public class WebhookController {

    private final WebhookDispatchService webhookDispatchService;

    @GetMapping("/health")
    public ResponseEntity getHealth() {
        return Response.OK.getApiResponse(webhookDispatchService.healthStatus());
    }

    @PostMapping("/linear/webhook")
    public ResponseEntity handleLinearWebhook(@RequestBody JsonNode payload) {
        webhookDispatchService.dispatch(payload);
        return Response.OK.getApiResponse(null);
    }
}
