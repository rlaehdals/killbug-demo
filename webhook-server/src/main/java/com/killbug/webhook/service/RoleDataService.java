package com.killbug.webhook.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.killbug.webhook.controller.request.RoleDataCreateRequest;
import com.killbug.webhook.controller.response.RoleDataResponse;
import com.killbug.webhook.entity.JuniorTask;
import com.killbug.webhook.entity.LeadDecision;
import com.killbug.webhook.entity.SeniorReview;
import com.killbug.webhook.repository.JuniorTaskRepository;
import com.killbug.webhook.repository.LeadDecisionRepository;
import com.killbug.webhook.repository.SeniorReviewRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class RoleDataService {

    private final JuniorTaskRepository juniorTaskRepository;
    private final SeniorReviewRepository seniorReviewRepository;
    private final LeadDecisionRepository leadDecisionRepository;

    @Transactional(readOnly = true)
    public List<RoleDataResponse> listJunior() {
        log.info("[role-data] junior 테이블 조회");
        return juniorTaskRepository.findAll().stream()
                .map(e -> RoleDataResponse.builder()
                        .id(e.getId())
                        .name(e.getName())
                        .content(e.getTask())
                        .createdAt(e.getCreatedAt())
                        .build())
                .toList();
    }

    @Transactional
    public RoleDataResponse createJunior(RoleDataCreateRequest request) {
        log.info("[role-data] junior 테이블 생성: {}", request.name());
        JuniorTask entity = JuniorTask.builder()
                .name(request.name())
                .task(request.content())
                .build();
        JuniorTask saved = juniorTaskRepository.save(entity);
        return RoleDataResponse.builder()
                .id(saved.getId())
                .name(saved.getName())
                .content(saved.getTask())
                .createdAt(saved.getCreatedAt())
                .build();
    }

    @Transactional(readOnly = true)
    public List<RoleDataResponse> listSenior() {
        log.info("[role-data] senior 테이블 조회");
        return seniorReviewRepository.findAll().stream()
                .map(e -> RoleDataResponse.builder()
                        .id(e.getId())
                        .name(e.getName())
                        .content(e.getReview())
                        .extra(e.getModule())
                        .createdAt(e.getCreatedAt())
                        .build())
                .toList();
    }

    @Transactional
    public RoleDataResponse createSenior(RoleDataCreateRequest request) {
        log.info("[role-data] senior 테이블 생성: {}", request.name());
        SeniorReview entity = SeniorReview.builder()
                .name(request.name())
                .review(request.content())
                .module(request.extra())
                .build();
        SeniorReview saved = seniorReviewRepository.save(entity);
        return RoleDataResponse.builder()
                .id(saved.getId())
                .name(saved.getName())
                .content(saved.getReview())
                .extra(saved.getModule())
                .createdAt(saved.getCreatedAt())
                .build();
    }

    @Transactional(readOnly = true)
    public List<RoleDataResponse> listLead() {
        log.info("[role-data] lead 테이블 조회");
        return leadDecisionRepository.findAll().stream()
                .map(e -> RoleDataResponse.builder()
                        .id(e.getId())
                        .name(e.getName())
                        .content(e.getDecision())
                        .extra(e.getPriority() != null ? "P" + e.getPriority() : null)
                        .createdAt(e.getCreatedAt())
                        .build())
                .toList();
    }

    @Transactional
    public RoleDataResponse createLead(RoleDataCreateRequest request) {
        log.info("[role-data] lead 테이블 생성: {}", request.name());
        Integer priority = null;
        if (request.extra() != null && !request.extra().isBlank()) {
            priority = Integer.parseInt(request.extra().replace("P", ""));
        }
        LeadDecision entity = LeadDecision.builder()
                .name(request.name())
                .decision(request.content())
                .priority(priority)
                .build();
        LeadDecision saved = leadDecisionRepository.save(entity);
        return RoleDataResponse.builder()
                .id(saved.getId())
                .name(saved.getName())
                .content(saved.getDecision())
                .extra("P" + saved.getPriority())
                .createdAt(saved.getCreatedAt())
                .build();
    }
}
