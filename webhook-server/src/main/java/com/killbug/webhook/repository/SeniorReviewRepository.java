package com.killbug.webhook.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.killbug.webhook.entity.SeniorReview;

public interface SeniorReviewRepository extends JpaRepository<SeniorReview, Long> {

    List<SeniorReview> findByModule(String module);

    List<SeniorReview> findByNameContaining(String name);
}
