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
@Table(name = "junior")
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class JuniorTask {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 500)
    private String task;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Builder
    public JuniorTask(String name, String task) {
        this.name = name;
        this.task = task;
        this.createdAt = LocalDateTime.now();
    }
}
