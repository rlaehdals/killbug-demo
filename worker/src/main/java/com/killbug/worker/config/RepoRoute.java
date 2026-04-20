package com.killbug.worker.config;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class RepoRoute {
    private String repository;
    private String localPath;
    private String baseBranch;
}
