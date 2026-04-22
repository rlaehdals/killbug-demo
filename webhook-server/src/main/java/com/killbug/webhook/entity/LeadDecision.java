package com.killbug.webhook.entity;

import java.time.LocalDateTime;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@Entity
@Table(name = "lead")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class LeadDecision {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 500)
    private String decision;

    @Column
    private Integer priority;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Builder
    public LeadDecision(String name, String decision, Integer priority) {
        this.name = name;
        this.decision = decision;
        this.priority = priority != null ? priority : 3;
        this.createdAt = LocalDateTime.now();
    }
}
