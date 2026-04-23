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
@Table(name = "senior")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class SeniorReview {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 500)
    private String review;

    @Column(length = 100)
    private String module;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Builder
    public SeniorReview(String name, String review, String module) {
        this.name = name;
        this.review = review;
        this.module = module;
        this.createdAt = LocalDateTime.now();
    }
}
