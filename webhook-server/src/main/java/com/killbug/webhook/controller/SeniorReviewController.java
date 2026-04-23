package com.killbug.webhook.controller;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.killbug.webhook.controller.response.SeniorReviewResponse;
import com.killbug.webhook.exception.Response;
import com.killbug.webhook.service.SeniorReviewService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/senior-reviews")
@RequiredArgsConstructor
public class SeniorReviewController {

    private final SeniorReviewService seniorReviewService;

    @GetMapping
    public ResponseEntity handleSearch(
            @RequestParam(required = false) String module, @RequestParam(required = false) String name) {
        List<SeniorReviewResponse> result = seniorReviewService.search(module, name);
        return Response.OK.getApiResponse(result);
    }
}
