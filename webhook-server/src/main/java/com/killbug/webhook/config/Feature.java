package com.killbug.webhook.config;

import java.util.ArrayList;
import java.util.List;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class Feature {
    private String name;
    private List<String> keywords = new ArrayList<>();
    private String linearTeamKey;
    private String repository;
    private List<Manager> feManagers = new ArrayList<>();
    private List<Manager> beManagers = new ArrayList<>();
}
