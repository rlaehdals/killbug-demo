package com.killbug.webhook.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.killbug.webhook.entity.LeadDecision;

public interface LeadDecisionRepository extends JpaRepository<LeadDecision, Long> {}
