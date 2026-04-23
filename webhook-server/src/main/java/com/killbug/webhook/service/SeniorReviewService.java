package com.killbug.webhook.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.killbug.webhook.controller.response.SeniorReviewResponse;
import com.killbug.webhook.entity.SeniorReview;
import com.killbug.webhook.repository.SeniorReviewRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class SeniorReviewService {

    private final SeniorReviewRepository seniorReviewRepository;

    @Transactional(readOnly = true)
    public List<SeniorReviewResponse> search(String module, String name) {
        List<SeniorReview> results;

        if (module != null && !module.isBlank()) {
            log.info("[senior-review] 모듈별 조회: {}", module);
            results = seniorReviewRepository.findByModule(module);
        } else if (name != null && !name.isBlank()) {
            log.info("[senior-review] 이름 검색: {}", name);
            results = seniorReviewRepository.findByNameContaining(name);
        } else {
            log.info("[senior-review] 전체 조회");
            results = seniorReviewRepository.findAll();
        }

        return results.stream().map(this::toResponse).toList();
    }

    private SeniorReviewResponse toResponse(SeniorReview entity) {
        return SeniorReviewResponse.builder()
                .id(entity.getId())
                .name(entity.getName())
                .review(entity.getReview())
                .module(entity.getModule())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
