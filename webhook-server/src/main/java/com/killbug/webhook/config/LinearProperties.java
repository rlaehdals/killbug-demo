package com.killbug.webhook.config;

import java.util.HashMap;
import java.util.Map;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
public class LinearProperties {
    private String apiUrl;
    private String apiKey;
    private Map<String, String> teamIds = new HashMap<>();
    private Map<String, String> labelIds = new HashMap<>();
    private Map<String, String> userMappings = new HashMap<>();
}
