package com.killbug.webhook.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.killbug.webhook.entity.JuniorTask;

public interface JuniorTaskRepository extends JpaRepository<JuniorTask, Long> {}
